#!/usr/bin/env python3
"""Plan-only post-closeout promotion-readiness gap analysis for v14.

This gate consumes the already-audited evidence package, shadow replay reviews,
promotion-decision plan, and no-promotion closeout review. It emits a read-only
gap matrix for future promotion-readiness work. It does not promote, deploy,
train, replay, generate candidates, modify Diffusion Planner, change an online
selector, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"

EVIDENCE_PACKAGE_SCHEMA = (
    "dp_camp_v14_public_simulator_default_off_selector_runtime_"
    "shadow_replay_promotion_evidence_package_construction_v1"
)
RESULT_REVIEW_SCHEMA = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_"
    "shadow_replay_result_review_v1"
)
DELTA_REVIEW_SCHEMA = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_"
    "shadow_vs_top1_delta_review_v1"
)
PROMOTION_PLAN_SCHEMA = (
    "dp_camp_v14_public_simulator_default_off_selector_runtime_"
    "shadow_replay_promotion_decision_from_evidence_package_plan_v1"
)
CLOSEOUT_REVIEW_SCHEMA = (
    "dp_camp_v14_public_simulator_default_off_selector_runtime_"
    "shadow_replay_promotion_decision_no_promotion_closeout_review_v1"
)

EVIDENCE_CONSTRUCTION_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_constructed"
)
RESULT_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "result_review_passed"
)
DELTA_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "shadow_vs_top1_delta_review_passed"
)
PROMOTION_PLAN_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_decision_plan_from_evidence_package_ready"
)
CLOSEOUT_REVIEW_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_decision_from_evidence_package_no_promotion_closeout_review_passed"
)
SOURCE_CLOSED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_decision_from_evidence_package_closed_no_further_action_"
    "without_new_eof_authorization"
)

AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_gap_analysis_plan_only"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_gap_analysis_plan_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_gap_analysis_plan_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_"
    "post_closeout_promotion_readiness_gap_analysis_static_review_only"
)

EXPECTED_PACKAGE_ENTRY_COUNT = 15
EXPECTED_ENTRY_NAMES = (
    "atom_scales_json",
    "offline_weights_npy",
    "runtime_manifest",
    "runtime_promotion_decision_plan",
    "runtime_result_review",
    "runtime_shadow_execution_sha256s",
    "shadow_vs_top1_delta_review",
    "source_preflight_json",
    "source_preflight_md",
    "source_preflight_sha256s",
    "static_review_json",
    "static_review_md",
    "static_review_sha256s",
    "training_artifact_static_review",
    "training_summary",
)
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
)

ARTIFACT_LAYOUTS = {
    "evidence_package": {
        "command": "COMMAND",
        "heads": "HEADS",
        "stdout": "stdout.txt",
        "stderr": "stderr.txt",
        "exit": "run.exit",
    },
    "result_review": {
        "command": "COMMAND.txt",
        "heads": "HEADS",
        "stdout": "logs/stdout.log",
        "stderr": "logs/stderr.log",
        "exit": "review.exit",
    },
    "delta_review": {
        "command": "COMMAND.txt",
        "heads": "HEADS",
        "stdout": "logs/stdout.log",
        "stderr": "logs/stderr.log",
        "exit": "review.exit",
    },
    "promotion_plan": {
        "command": "COMMAND",
        "heads": "HEADS",
        "stdout": "stdout.txt",
        "stderr": "stderr.txt",
        "exit": "run.exit",
    },
    "closeout_review": {
        "command": "COMMAND",
        "heads": "HEADS",
        "stdout": "stdout.txt",
        "stderr": "stderr.txt",
        "exit": "run.exit",
    },
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence_package_artifact_dir", type=Path, required=True)
    parser.add_argument("--result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--delta_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--promotion_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--closeout_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--evidence_manifest_json", type=Path, required=True)
    parser.add_argument("--evidence_construction_json", type=Path, required=True)
    parser.add_argument("--result_review_json", type=Path, required=True)
    parser.add_argument("--shadow_vs_top1_delta_review_json", type=Path, required=True)
    parser.add_argument("--promotion_decision_plan_json", type=Path, required=True)
    parser.add_argument("--no_promotion_closeout_review_json", type=Path, required=True)
    parser.add_argument("--evidence_package_sha256s", type=Path, required=True)
    parser.add_argument("--evidence_construction_sha256s", type=Path, required=True)
    parser.add_argument("--result_review_sha256s", type=Path, required=True)
    parser.add_argument("--shadow_vs_top1_delta_review_sha256s", type=Path, required=True)
    parser.add_argument("--promotion_decision_plan_sha256s", type=Path, required=True)
    parser.add_argument("--no_promotion_closeout_review_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_post_closeout_promotion_readiness_gap_analysis",
        action="store_true",
        help="Explicit opt-in for read-only post-closeout gap analysis.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        evidence_package_artifact_dir=args.evidence_package_artifact_dir,
        result_review_artifact_dir=args.result_review_artifact_dir,
        delta_review_artifact_dir=args.delta_review_artifact_dir,
        promotion_plan_artifact_dir=args.promotion_plan_artifact_dir,
        closeout_review_artifact_dir=args.closeout_review_artifact_dir,
        evidence_manifest_json=args.evidence_manifest_json,
        evidence_construction_json=args.evidence_construction_json,
        result_review_json=args.result_review_json,
        shadow_vs_top1_delta_review_json=args.shadow_vs_top1_delta_review_json,
        promotion_decision_plan_json=args.promotion_decision_plan_json,
        no_promotion_closeout_review_json=args.no_promotion_closeout_review_json,
        evidence_package_sha256s=args.evidence_package_sha256s,
        evidence_construction_sha256s=args.evidence_construction_sha256s,
        result_review_sha256s=args.result_review_sha256s,
        shadow_vs_top1_delta_review_sha256s=args.shadow_vs_top1_delta_review_sha256s,
        promotion_decision_plan_sha256s=args.promotion_decision_plan_sha256s,
        no_promotion_closeout_review_sha256s=args.no_promotion_closeout_review_sha256s,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_post_closeout_promotion_readiness_gap_analysis,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    evidence_package_artifact_dir: Path,
    result_review_artifact_dir: Path,
    delta_review_artifact_dir: Path,
    promotion_plan_artifact_dir: Path,
    closeout_review_artifact_dir: Path,
    evidence_manifest_json: Path,
    evidence_construction_json: Path,
    result_review_json: Path,
    shadow_vs_top1_delta_review_json: Path,
    promotion_decision_plan_json: Path,
    no_promotion_closeout_review_json: Path,
    evidence_package_sha256s: Path,
    evidence_construction_sha256s: Path,
    result_review_sha256s: Path,
    shadow_vs_top1_delta_review_sha256s: Path,
    promotion_decision_plan_sha256s: Path,
    no_promotion_closeout_review_sha256s: Path,
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
    artifact_dirs = {
        "evidence_package": evidence_package_artifact_dir.resolve(),
        "result_review": result_review_artifact_dir.resolve(),
        "delta_review": delta_review_artifact_dir.resolve(),
        "promotion_plan": promotion_plan_artifact_dir.resolve(),
        "closeout_review": closeout_review_artifact_dir.resolve(),
    }
    json_paths = {
        "evidence_manifest_json": evidence_manifest_json.resolve(),
        "evidence_construction_json": evidence_construction_json.resolve(),
        "result_review_json": result_review_json.resolve(),
        "shadow_vs_top1_delta_review_json": shadow_vs_top1_delta_review_json.resolve(),
        "promotion_decision_plan_json": promotion_decision_plan_json.resolve(),
        "no_promotion_closeout_review_json": no_promotion_closeout_review_json.resolve(),
    }
    sha_paths = {
        "evidence_package_sha256s": evidence_package_sha256s.resolve(),
        "evidence_construction_sha256s": evidence_construction_sha256s.resolve(),
        "result_review_sha256s": result_review_sha256s.resolve(),
        "shadow_vs_top1_delta_review_sha256s": shadow_vs_top1_delta_review_sha256s.resolve(),
        "promotion_decision_plan_sha256s": promotion_decision_plan_sha256s.resolve(),
        "no_promotion_closeout_review_sha256s": no_promotion_closeout_review_sha256s.resolve(),
    }
    docs = {
        "v14_audit_md": v14_audit_md.resolve(),
        "current_status_md": current_status_md.resolve(),
    }
    source_data = {name: _read_json_dict(path) for name, path in json_paths.items()}
    source_sha256s = {name: _read_sha256sums(path) for name, path in sha_paths.items()}
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    checks: list[dict[str, Any]] = []

    for name, path in artifact_dirs.items():
        checks.extend(_path_checks(f"{name}_artifact_dir", path, require_file=False))
    for name, path in {**json_paths, **sha_paths, **docs}.items():
        checks.extend(_path_checks(name, path, require_file=True))
    checks.extend(
        [
            _expect("gap_analysis_enabled", enabled, True),
            _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
            _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
            _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
            _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        ]
    )
    checks.extend(_artifact_checks(artifact_dirs))
    checks.extend(_source_sha_checks(json_paths, source_sha256s))
    checks.extend(_evidence_manifest_checks(source_data["evidence_manifest_json"]))
    checks.extend(_source_json_checks(source_data))
    checks.extend(_audit_checks(v14_text, status_text))
    passed = all(check["passed"] for check in checks)

    return {
        "schema_version": (
            "dp_camp_v14_public_simulator_post_closeout_"
            "promotion_readiness_gap_analysis_plan_v1"
        ),
        "analysis": {
            "label": label,
            "plan_only": True,
            "read_only": True,
            "artifact_dirs": {name: str(path) for name, path in artifact_dirs.items()},
            "source_json_paths": {name: str(path) for name, path in json_paths.items()},
            "source_sha256s_paths": {name: str(path) for name, path in sha_paths.items()},
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
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
                "This gate only organizes post-closeout evidence gaps. CAMP "
                "remains a default-off shadow reranker over fixed DP candidate "
                f"tensors with affine {SCORE_EXPRESSION} over approved atoms "
                "and nonnegative simplex weights."
            ),
        },
        "source_hashes": {
            **{
                name: _sha256(path) if path.is_file() else None
                for name, path in json_paths.items()
            },
            **{
                name: _sha256(path) if path.is_file() else None
                for name, path in sha_paths.items()
            },
            "v14_audit_md": _sha256(v14_audit_md) if v14_audit_md.is_file() else None,
            "current_status_md": _sha256(current_status_md)
            if current_status_md.is_file()
            else None,
        },
        "source_summaries": _source_summaries(source_data),
        "evidence_support": _evidence_support(),
        "evidence_gaps": _evidence_gaps(),
        "promotion_readiness_matrix": _promotion_readiness_matrix(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "gap_analysis_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "post_closeout_promotion_readiness_gap_analysis.json", report)
    (output_dir / "post_closeout_promotion_readiness_gap_analysis.md").write_text(
        _render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def _artifact_checks(artifact_dirs: dict[str, Path]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for artifact_name, root in artifact_dirs.items():
        layout = ARTIFACT_LAYOUTS[artifact_name]
        sha_path = root / "SHA256SUMS"
        root_sha256s = _read_sha256sums(sha_path)
        heads = _parse_key_values(_read_text(root / layout["heads"]))
        for role, rel in layout.items():
            path = root / rel
            if role == "stderr":
                checks.append(_check(f"{artifact_name}_{role}_exists", path.is_file(), str(path), "file"))
            else:
                checks.extend(_path_checks(f"{artifact_name}_{role}", path, require_file=True))
            if role == "exit":
                checks.append(_expect(f"{artifact_name}_{role}_zero", _read_text(path).strip(), "0"))
            checks.append(
                _sha256sums_expect(
                    f"{artifact_name}_{role}_root_sha",
                    path,
                    root_sha256s,
                    _sha_keys(rel),
                )
            )
        checks.append(_check(f"{artifact_name}_root_sha256s_parseable", bool(root_sha256s), sorted(root_sha256s), "nonempty"))
        checks.append(_expect(f"{artifact_name}_heads_dp_fixed", heads.get("dp_head"), FIXED_DP_HEAD))
        if "camp_head" in heads:
            checks.append(_check(f"{artifact_name}_heads_camp_head_is_sha", _is_git_sha(heads["camp_head"]), heads["camp_head"], "40-char git sha"))
        if "camp_origin_main" in heads:
            checks.append(_check(f"{artifact_name}_heads_camp_origin_is_sha", _is_git_sha(heads["camp_origin_main"]), heads["camp_origin_main"], "40-char git sha"))
        if "camp_head" in heads and "camp_origin_main" in heads:
            checks.append(_expect(f"{artifact_name}_heads_camp_matches_origin", heads["camp_head"], heads["camp_origin_main"]))
    return checks


def _source_sha_checks(
    json_paths: dict[str, Path],
    source_sha256s: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    mapping = {
        "evidence_manifest_json": "evidence_package_sha256s",
        "evidence_construction_json": "evidence_construction_sha256s",
        "result_review_json": "result_review_sha256s",
        "shadow_vs_top1_delta_review_json": "shadow_vs_top1_delta_review_sha256s",
        "promotion_decision_plan_json": "promotion_decision_plan_sha256s",
        "no_promotion_closeout_review_json": "no_promotion_closeout_review_sha256s",
    }
    checks: list[dict[str, Any]] = []
    for json_name, sha_name in mapping.items():
        path = json_paths[json_name]
        checks.append(
            _sha256sums_expect(
                f"{json_name}_listed_in_{sha_name}",
                path,
                source_sha256s[sha_name],
                (path.name, f"./{path.name}"),
            )
        )
    return checks


def _evidence_manifest_checks(evidence_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    entries = _list(evidence_manifest.get("entries"))
    by_name = {entry.get("name"): entry for entry in entries if isinstance(entry, dict)}
    checks = [
        _expect("evidence_manifest_schema", evidence_manifest.get("schema_version"), EVIDENCE_PACKAGE_SCHEMA),
        _expect("evidence_manifest_score_expression", evidence_manifest.get("score_expression"), SCORE_EXPRESSION),
        _expect("evidence_manifest_source_static_review_passed", evidence_manifest.get("source_static_review_passed"), True),
        _expect("evidence_manifest_entry_count", len(entries), EXPECTED_PACKAGE_ENTRY_COUNT),
        _expect("evidence_manifest_entry_names", sorted(by_name), sorted(EXPECTED_ENTRY_NAMES)),
    ]
    for name in EXPECTED_ENTRY_NAMES:
        entry = _dict(by_name.get(name))
        package_path = Path(str(entry.get("package_path", "")))
        package_sha = _sha256(package_path) if package_path.is_file() else None
        checks.extend(
            [
                _expect(f"evidence_entry_{name}_package_exists_flag", entry.get("package_exists"), True),
                _expect(f"evidence_entry_{name}_hash_matches_flag", entry.get("hash_matches"), True),
                _check(f"evidence_entry_{name}_package_file_exists", package_path.is_file(), str(package_path), "file"),
                _expect(f"evidence_entry_{name}_package_sha_matches_manifest", package_sha, entry.get("package_sha256")),
            ]
        )
    for name in BLOCKED_ACTIONS:
        checks.append(_expect(f"evidence_manifest_blocked_{name}", _dict(evidence_manifest.get("blocked_actions")).get(name), False))
    return checks


def _source_json_checks(source_data: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    specs = {
        "evidence_construction_json": (EVIDENCE_PACKAGE_SCHEMA, EVIDENCE_CONSTRUCTION_STATUS),
        "result_review_json": (RESULT_REVIEW_SCHEMA, RESULT_REVIEW_STATUS),
        "shadow_vs_top1_delta_review_json": (DELTA_REVIEW_SCHEMA, DELTA_REVIEW_STATUS),
        "promotion_decision_plan_json": (PROMOTION_PLAN_SCHEMA, PROMOTION_PLAN_STATUS),
        "no_promotion_closeout_review_json": (CLOSEOUT_REVIEW_SCHEMA, CLOSEOUT_REVIEW_STATUS),
    }
    checks: list[dict[str, Any]] = []
    for name, (schema, status) in specs.items():
        payload = source_data[name]
        decision = _dict(payload.get("final_decision"))
        analysis = _dict(payload.get("analysis"))
        blocked = _dict(payload.get("blocked_actions"))
        checks.extend(
            [
                _expect(f"{name}_schema", payload.get("schema_version"), schema),
                _expect(f"{name}_passed", decision.get("passed"), True),
                _expect(f"{name}_status", decision.get("status"), status),
                _expect(f"{name}_failed_checks", decision.get("failed_checks"), []),
                _expect(f"{name}_score_expression", _score_expression(payload), SCORE_EXPRESSION),
            ]
        )
        for flag in ("training_execution", "replay_execution", "candidate_generation", "dp_modification"):
            if flag in analysis:
                checks.append(_expect(f"{name}_analysis_{flag}", analysis.get(flag), False))
        for flag in ("online_selector_change", "promotion_executed", "deployment_executed"):
            if flag in analysis:
                checks.append(_expect(f"{name}_analysis_{flag}", analysis.get(flag), False))
        if "safety_or_camp_over_dp_claim" in analysis:
            checks.append(_expect(f"{name}_analysis_safety_or_camp_over_dp_claim", analysis.get("safety_or_camp_over_dp_claim"), False))
        for action in BLOCKED_ACTIONS:
            if action in decision:
                checks.append(_expect(f"{name}_decision_{action}", decision.get(action), False))
            if action in blocked:
                checks.append(_expect(f"{name}_blocked_{action}", blocked.get(action), False))
        for flag in EXECUTION_FLAGS:
            if flag in decision:
                checks.append(_expect(f"{name}_decision_{flag}", decision.get(flag), False))
    promotion_plan = _dict(source_data["promotion_decision_plan_json"].get("final_decision"))
    closeout = _dict(source_data["no_promotion_closeout_review_json"].get("final_decision"))
    checks.extend(
        [
            _expect("promotion_plan_recommendation", promotion_plan.get("recommendation"), "do_not_promote_from_current_evidence_package_alone"),
            _expect("promotion_plan_immediate_action", promotion_plan.get("immediate_action"), "record_no_promotion_closeout_only"),
            _expect("promotion_plan_ready_flag", promotion_plan.get("promotion_decision_from_evidence_package_plan_ready"), True),
            _expect("closeout_recommendation", closeout.get("recommendation"), "keep_default_off_no_promotion_from_current_evidence_package"),
            _expect("closeout_complete", closeout.get("no_promotion_closeout_complete"), True),
            _expect("closeout_future_promotion_requires_new_eof", closeout.get("future_promotion_requires_new_eof_and_explicit_authorization"), True),
        ]
    )
    return checks


def _audit_checks(v14_text: str, status_text: str) -> list[dict[str, Any]]:
    return [
        _expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), CLOSEOUT_REVIEW_STATUS),
        _expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), SOURCE_CLOSED_NEXT_WORK),
        _expect("status_doc_latest_status", _latest_value(status_text, "current_v14_status"), CLOSEOUT_REVIEW_STATUS),
        _expect("status_doc_latest_next_work", _latest_value(status_text, "next_work_target"), SOURCE_CLOSED_NEXT_WORK),
        _expect("audit_closeout_complete", _latest_value(v14_text, "default_off_shadow_selector_runtime_no_promotion_closeout_complete"), "True"),
        _expect("audit_future_promotion_requires_new_eof", _latest_value(v14_text, "future_promotion_requires_new_eof_and_explicit_authorization"), "True"),
        _expect("audit_selector_promotion_authorized", _latest_value(v14_text, "selector_promotion_authorized"), "False"),
        _expect("audit_deployment_authorized", _latest_value(v14_text, "deployment_authorized"), "False"),
        _expect("audit_safety_benefit_claim_authorized", _latest_value(v14_text, "safety_benefit_claim_authorized"), "False"),
        _expect("audit_camp_over_dp_top1_claim_authorized", _latest_value(v14_text, "camp_over_dp_top1_claim_authorized"), "False"),
    ]


def _source_summaries(source_data: dict[str, dict[str, Any]]) -> dict[str, Any]:
    summaries = {}
    for name, payload in source_data.items():
        decision = _dict(payload.get("final_decision"))
        summaries[name] = {
            "schema_version": payload.get("schema_version"),
            "status": decision.get("status"),
            "passed": decision.get("passed"),
            "failed_checks": decision.get("failed_checks"),
            "authorized_next_work": decision.get("authorized_next_work"),
            "recommendation": decision.get("recommendation"),
            "score_expression": _score_expression(payload),
        }
    manifest = source_data["evidence_manifest_json"]
    summaries["evidence_manifest_json"].update(
        {
            "entry_count": len(_list(manifest.get("entries"))),
            "source_static_review_passed": manifest.get("source_static_review_passed"),
            "score_expression": manifest.get("score_expression"),
        }
    )
    return summaries


def _evidence_support() -> list[dict[str, Any]]:
    return [
        {
            "name": "fixed_dp_candidate_tensor_chain",
            "status": "supported_for_audit",
            "scope": "CAMP reranks fixed DP candidate tensors only",
        },
        {
            "name": "default_off_shadow_selector_runtime",
            "status": "supported_for_audit",
            "scope": "shadow selection is logged without changing DP Top-1 execution",
        },
        {
            "name": "static_masked_objective_delta",
            "status": "supported_for_audit",
            "scope": "usable as static evidence only, not safety or deployment proof",
        },
        {
            "name": "no_promotion_closeout",
            "status": "supported_for_audit",
            "scope": "current evidence package is closed without promotion",
        },
    ]


def _evidence_gaps() -> list[dict[str, Any]]:
    return [
        {
            "category": "active_selector_promotion",
            "gap_status": "open",
            "current_evidence_limit": "No active/executed selector or online effect evidence is authorized.",
            "required_future_evidence": [
                "explicit future EOF and authorization for a promotion gate",
                "predefined promotion thresholds and no-go conditions",
                "read-only static review before any activation path exists",
            ],
        },
        {
            "category": "deployment_fail_closed",
            "gap_status": "open",
            "current_evidence_limit": "Default-off shadow evidence does not prove deployable fail-closed behavior.",
            "required_future_evidence": [
                "activation/runbook plan with rollback and config gating",
                "fail-closed tests for missing weights, malformed tensors, and DP mismatch",
                "audit trail showing DP Top-1 remains the executed fallback",
            ],
        },
        {
            "category": "safety_claim",
            "gap_status": "open",
            "current_evidence_limit": "Static objective deltas are not safety-benefit evidence.",
            "required_future_evidence": [
                "predeclared safety metrics and thresholds",
                "failure-mode and OOD scenario review",
                "statistical uncertainty analysis over an allowed evaluation split",
            ],
        },
        {
            "category": "camp_over_dp_top1_claim",
            "gap_status": "open",
            "current_evidence_limit": "Current package does not prove CAMP superiority over DP Top-1.",
            "required_future_evidence": [
                "claim-specific metric definition before evaluation",
                "held-out comparison against fixed DP Top-1 under the same split contract",
                "confidence intervals and per-scenario regression checks",
            ],
        },
        {
            "category": "evaluation_coverage",
            "gap_status": "open",
            "current_evidence_limit": "Current evidence is limited to the audited public-simulator scope.",
            "required_future_evidence": [
                "allowed non-Full36 evaluation manifest",
                "explicit exclusion of formal seeds 11/12/13",
                "zero-overlap preservation and candidate-source provenance checks",
            ],
        },
        {
            "category": "governance_authorization",
            "gap_status": "open",
            "current_evidence_limit": "Closeout forbids promotion/deployment without new EOF and authorization.",
            "required_future_evidence": [
                "separate EOF for each future gate",
                "static review that no forbidden action is bundled into planning",
                "audit text preserving no safety/CAMP-over-DP claim unless proven later",
            ],
        },
    ]


def _promotion_readiness_matrix() -> list[dict[str, Any]]:
    return [
        {
            "decision_surface": "promotion_readiness",
            "current_state": "not_ready_for_active_promotion",
            "next_allowed_gate": AUTHORIZED_NEXT_WORK,
            "promotion_authorized": False,
        },
        {
            "decision_surface": "deployment_readiness",
            "current_state": "not_ready_for_deployment",
            "next_allowed_gate": AUTHORIZED_NEXT_WORK,
            "deployment_authorized": False,
        },
        {
            "decision_surface": "safety_or_superiority_claim",
            "current_state": "not_ready_for_claim",
            "next_allowed_gate": AUTHORIZED_NEXT_WORK,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    ]


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "post_closeout_promotion_readiness_gap_analysis_ready": bool(passed),
        "recommendation": "do_not_promote_or_deploy_from_current_evidence_package",
        "immediate_action": "static_review_this_gap_analysis_only",
        "score_expression": SCORE_EXPRESSION,
        "training_executed_by_this_gate": False,
        "replay_executed_by_this_gate": False,
        "candidate_generation_executed_by_this_gate": False,
        "dp_modified_by_this_gate": False,
        "promotion_executed_by_this_gate": False,
        "deployment_executed_by_this_gate": False,
    }
    for name in BLOCKED_ACTIONS:
        decision[name] = False
    return decision


def _failure_class(failed: list[str]) -> str:
    failed_set = set(failed)
    if "gap_analysis_enabled" in failed_set:
        return "explicit_post_closeout_gap_analysis_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("status_doc_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.endswith("_root_sha") or "_listed_in_" in name for name in failed):
        return "source_artifact_sha256_mismatch"
    if any(name.startswith("evidence_manifest") or name.startswith("evidence_entry_") for name in failed):
        return "evidence_package_contract_failure"
    if any(name.endswith("_schema") or name.endswith("_status") or name.endswith("_passed") for name in failed):
        return "source_gate_contract_failure"
    if any("_decision_" in name or "_blocked_" in name or "_analysis_" in name for name in failed):
        return "boundary_contract_failure"
    if any(name.endswith("_exists") or name.endswith("_nonempty") for name in failed):
        return "source_file_missing_or_empty"
    return "post_closeout_promotion_readiness_gap_analysis_failure"


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Post-Closeout Promotion-Readiness Gap Analysis",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Recommendation: `{decision['recommendation']}`",
        f"- Immediate action: `{decision['immediate_action']}`",
        f"- Authorized current work: `{decision['authorized_current_work']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Selector promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        f"- CAMP-over-DP Top-1 claim authorized: `{decision['camp_over_dp_top1_claim_authorized']}`",
        "",
        "## Evidence Support",
        "",
    ]
    for item in report["evidence_support"]:
        lines.append(f"- `{item['name']}`: `{item['status']}` - {item['scope']}")
    lines.extend(["", "## Evidence Gaps", ""])
    for gap in report["evidence_gaps"]:
        lines.append(f"### {gap['category']}")
        lines.append("")
        lines.append(f"- Gap status: `{gap['gap_status']}`")
        lines.append(f"- Current evidence limit: {gap['current_evidence_limit']}")
        lines.append("- Required future evidence:")
        for requirement in gap["required_future_evidence"]:
            lines.append(f"  - {requirement}")
        lines.append("")
    lines.extend(
        [
            "## Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This plan is read-only. It does not train, replay, generate "
            "candidates, modify DP, change an online selector, promote atoms "
            "or selectors, deploy, or authorize safety/CAMP-over-DP claims.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["gap_analysis_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{_compact(check.get('observed'))}` | `{_compact(check.get('expected'))}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _path_checks(name: str, path: Path, *, require_file: bool) -> list[dict[str, Any]]:
    if require_file:
        exists = path.is_file()
        expected = "file"
        size = path.stat().st_size if exists else None
        nonempty = exists and bool(size)
    else:
        exists = path.is_dir()
        expected = "directory"
        size = len(list(path.iterdir())) if exists else None
        nonempty = exists and bool(size)
    return [
        _check(f"{name}_exists", exists, str(path), expected),
        _check(
            f"{name}_nonempty",
            nonempty,
            size,
            "nonempty",
        ),
    ]


def _sha256sums_expect(
    name: str,
    path: Path,
    sha256sums: dict[str, str],
    keys: tuple[str, ...],
) -> dict[str, Any]:
    observed_sha = _sha256(path) if path.is_file() else None
    expected_sha = next((sha256sums[key] for key in keys if key in sha256sums), None)
    return _expect(name, observed_sha, expected_sha)


def _sha_keys(rel: str) -> tuple[str, ...]:
    return (rel, f"./{rel}", Path(rel).name)


def _score_expression(payload: dict[str, Any]) -> Any:
    decision = _dict(payload.get("final_decision"))
    analysis = _dict(payload.get("analysis"))
    source_summary = _dict(payload.get("source_summary"))
    return (
        decision.get("score_expression")
        or analysis.get("score_expression")
        or source_summary.get("score_expression")
        or payload.get("score_expression")
    )


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": _stable(observed),
        "expected": _stable(expected),
    }


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
            values[key] = parts[0]
            values[key.removeprefix("./")] = parts[0]
            values[Path(key).name] = parts[0]
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


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    values = [
        line.split("=", 1)[1].strip()
        for line in text.splitlines()
        if line.startswith(prefix)
    ]
    return values[-1] if values else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    rows = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name != "SHA256SUMS":
            rows.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


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
    text = json.dumps(_stable(value), sort_keys=True)
    return text if len(text) <= 140 else text[:137] + "..."


if __name__ == "__main__":
    raise SystemExit(main())
