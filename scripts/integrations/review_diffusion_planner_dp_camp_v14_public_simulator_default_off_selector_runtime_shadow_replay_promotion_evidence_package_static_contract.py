#!/usr/bin/env python3
"""Static review for the v14 runtime promotion evidence package preflight.

This gate reviews the read-only evidence-package preflight artifact. It checks
immutable hashes and boundary contracts only. It does not promote, deploy,
train, replay, generate candidates, modify Diffusion Planner, change a
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
SOURCE_PREFLIGHT_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_selector_runtime_"
    "shadow_replay_promotion_evidence_package_preflight_v1"
)
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_selector_runtime_"
    "shadow_replay_promotion_evidence_package_static_review_v1"
)
SOURCE_PREFLIGHT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_preflight_ready"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_static_review_only"
)
SOURCE_RERUN_DECISION_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_static_review_rerun_requires_user_decision"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_static_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_static_review_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_"
    "promotion_evidence_package_construction_only"
)
SOURCE_RUNTIME_MANIFEST_SCHEMA = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1"
)

EXPECTED_ARTIFACT_NAMES = (
    "runtime_promotion_decision_plan",
    "runtime_result_review",
    "shadow_vs_top1_delta_review",
    "runtime_manifest",
    "training_artifact_static_review",
    "training_summary",
    "offline_weights_npy",
    "atom_scales_json",
    "runtime_shadow_execution_sha256s",
)

DEFAULT_EXPECTED_COUNTS = {
    "selection_log_count": 32,
    "validation_summary_count": 32,
    "replay_summary_count": 32,
    "records": 3200,
    "executed_top1_records": 3200,
    "shadow_selected_index_nonzero_records": 2832,
    "feasible_records": 2914,
    "used_fallback_records": 286,
    "selection_score_better_records": 2832,
    "selection_score_tie_records": 368,
    "selection_score_worse_records": 0,
    "selection_score_uncomparable_records": 0,
    "training_records": 2914,
    "dropped_records_without_feasible_candidate": 286,
    "num_candidates": 8,
    "num_atoms": 9,
}

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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime_promotion_evidence_package_preflight_json", type=Path, required=True)
    parser.add_argument("--runtime_promotion_evidence_package_preflight_md", type=Path, required=True)
    parser.add_argument("--runtime_promotion_evidence_package_preflight_sha256s", type=Path, required=True)
    parser.add_argument("--preflight_script_py", type=Path, required=True)
    parser.add_argument("--preflight_test_py", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    for name, default in DEFAULT_EXPECTED_COUNTS.items():
        parser.add_argument(f"--expected_{name}", type=int, default=default)
    parser.add_argument(
        "--enable_v14_runtime_promotion_evidence_package_static_review",
        action="store_true",
        help="Explicit opt-in for static review only; no promotion action is executed.",
    )
    parser.add_argument(
        "--enable_v14_runtime_promotion_evidence_package_static_review_rerun_after_user_authorization",
        action="store_true",
        help=(
            "Explicit opt-in for rerunning this static review after a recorded "
            "failed attempt and user authorization."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        runtime_promotion_evidence_package_preflight_json=(
            args.runtime_promotion_evidence_package_preflight_json
        ),
        runtime_promotion_evidence_package_preflight_md=(
            args.runtime_promotion_evidence_package_preflight_md
        ),
        runtime_promotion_evidence_package_preflight_sha256s=(
            args.runtime_promotion_evidence_package_preflight_sha256s
        ),
        preflight_script_py=args.preflight_script_py,
        preflight_test_py=args.preflight_test_py,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=args.enable_v14_runtime_promotion_evidence_package_static_review,
        rerun_after_user_authorization=(
            args.enable_v14_runtime_promotion_evidence_package_static_review_rerun_after_user_authorization
        ),
        expected_counts={
            name: getattr(args, f"expected_{name}")
            for name in DEFAULT_EXPECTED_COUNTS
        },
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    runtime_promotion_evidence_package_preflight_json: Path,
    runtime_promotion_evidence_package_preflight_md: Path,
    runtime_promotion_evidence_package_preflight_sha256s: Path,
    preflight_script_py: Path,
    preflight_test_py: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    label: str | None = None,
    enabled: bool = False,
    rerun_after_user_authorization: bool = False,
    expected_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    expected = dict(DEFAULT_EXPECTED_COUNTS)
    if expected_counts:
        expected.update(expected_counts)

    paths = {
        "runtime_promotion_evidence_package_preflight_json": runtime_promotion_evidence_package_preflight_json,
        "runtime_promotion_evidence_package_preflight_md": runtime_promotion_evidence_package_preflight_md,
        "runtime_promotion_evidence_package_preflight_sha256s": runtime_promotion_evidence_package_preflight_sha256s,
        "preflight_script_py": preflight_script_py,
        "preflight_test_py": preflight_test_py,
        "v14_audit_md": v14_audit_md,
        "current_status_md": current_status_md,
    }
    preflight = _read_json_dict(runtime_promotion_evidence_package_preflight_json)
    sha256sums = _read_sha256sums(runtime_promotion_evidence_package_preflight_sha256s)
    texts = {
        name: path.read_text(encoding="utf-8") if path.is_file() else ""
        for name, path in paths.items()
        if path.suffix != ".json"
    }
    checks: list[dict[str, Any]] = [
        _expect("static_review_enabled", enabled, True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
    ]
    for name, path in paths.items():
        checks.extend(_file_checks(name, path))

    checks.extend(
        _preflight_file_hash_checks(
            runtime_promotion_evidence_package_preflight_json,
            runtime_promotion_evidence_package_preflight_md,
            sha256sums,
        )
    )
    checks.extend(_source_preflight_checks(preflight, expected))
    checks.extend(_artifact_manifest_checks(preflight))
    checks.extend(_source_surface_checks(texts.get("preflight_script_py", ""), texts.get("preflight_test_py", "")))
    checks.extend(
        _audit_contract_checks(
            texts.get("v14_audit_md", ""),
            texts.get("current_status_md", ""),
            rerun_after_user_authorization=rerun_after_user_authorization,
        )
    )

    passed = all(check["passed"] for check in checks)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "static_review_only": True,
            "rerun_after_user_authorization": bool(rerun_after_user_authorization),
            "runtime_promotion_evidence_package_preflight_json": str(
                runtime_promotion_evidence_package_preflight_json.resolve()
            ),
            "runtime_promotion_evidence_package_preflight_md": str(
                runtime_promotion_evidence_package_preflight_md.resolve()
            ),
            "runtime_promotion_evidence_package_preflight_sha256s": str(
                runtime_promotion_evidence_package_preflight_sha256s.resolve()
            ),
            "preflight_script_py": str(preflight_script_py.resolve()),
            "preflight_test_py": str(preflight_test_py.resolve()),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir.resolve()),
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "promotion_executed": False,
            "deployment_executed": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation": False,
            "online_selector_change": False,
            "dp_modification": False,
            "safety_or_camp_over_dp_claim": False,
            "math_boundary": (
                "This static review only audits the evidence package preflight. "
                "CAMP remains a default-off shadow reranker over fixed DP "
                "candidate tensors, using affine score_k(w)=a_k^T w over "
                "approved atoms with nonnegative simplex weights. Executed "
                "trajectory selection remains DP Top-1."
            ),
        },
        "source_hashes": {
            name: _sha256(path) if path.is_file() else None
            for name, path in paths.items()
        },
        "source_preflight_summary": _source_preflight_summary(preflight),
        "artifact_manifest_review": _artifact_manifest_review(preflight),
        "review_scope": _review_scope(),
        "forbidden_paths": _forbidden_paths(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "review_checks": checks,
        "final_decision": _decision(passed, checks),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "runtime_promotion_evidence_package_static_review.json", report)
    (output_dir / "runtime_promotion_evidence_package_static_review.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["source_preflight_summary"]
    lines = [
        "# V14 Runtime Promotion Evidence-Package Static Review",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Evidence package construction authorized: `{decision['evidence_package_construction_authorized']}`",
        f"- Selector promotion authorized: `{decision['selector_promotion_authorized']}`",
        f"- Deployment authorized: `{decision['deployment_authorized']}`",
        f"- Safety benefit claim authorized: `{decision['safety_benefit_claim_authorized']}`",
        f"- CAMP-over-DP-Top1 claim authorized: `{decision['camp_over_dp_top1_claim_authorized']}`",
        "",
        "## Source Preflight",
        "",
        f"- Preflight status: `{summary.get('status')}`",
        f"- Preflight passed: `{summary.get('passed')}`",
        f"- Authorized next work: `{summary.get('authorized_next_work')}`",
        f"- Artifact entries: `{summary.get('artifact_entries')}`",
        f"- Records: `{summary.get('records')}`",
        f"- Executed DP Top-1 records: `{summary.get('executed_top1_records')}`",
        f"- Shadow non-Top-1 records: `{summary.get('shadow_selected_index_nonzero_records')}`",
        f"- Static masked objective better/tie/worse/uncomparable: `{summary.get('selection_score_better_records')}` / `{summary.get('selection_score_tie_records')}` / `{summary.get('selection_score_worse_records')}` / `{summary.get('selection_score_uncomparable_records')}`",
        f"- Training records / dropped all-infeasible: `{summary.get('training_records')}` / `{summary.get('dropped_records_without_feasible_candidate')}`",
        f"- Runtime manifest schema: `{summary.get('runtime_manifest_schema_version')}`",
        f"- Score expression: `{summary.get('score_expression')}`",
        "",
        "## Artifact Manifest Review",
        "",
        "| Artifact | Exists | Hash matches | SHA-256 |",
        "| --- | ---: | ---: | --- |",
    ]
    for item in report["artifact_manifest_review"]:
        lines.append(
            f"| `{item['name']}` | `{item['exists']}` | "
            f"`{item['hash_matches']}` | `{item['sha256']}` |"
        )
    lines.extend(["", "## Review Scope", ""])
    for item in report["review_scope"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Forbidden Paths", ""])
    for item in report["forbidden_paths"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This static review did not promote atoms or selectors, deploy, "
            "train CAMP, run replay, generate candidates, modify DP, change "
            "online selection, or authorize safety/CAMP-over-DP claims.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["review_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{_compact(check['observed'])}` | `{_compact(check['expected'])}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _source_preflight_checks(
    preflight: dict[str, Any],
    expected: dict[str, int],
) -> list[dict[str, Any]]:
    decision = _dict(preflight.get("final_decision"))
    analysis = _dict(preflight.get("analysis"))
    source_summary = _dict(preflight.get("source_summary"))
    static_contract = _dict(preflight.get("static_integration_contract"))
    blocked = _dict(preflight.get("blocked_actions"))
    checks = [
        _expect("source_preflight_schema", preflight.get("schema_version"), SOURCE_PREFLIGHT_SCHEMA_VERSION),
        _expect("source_preflight_status", decision.get("status"), SOURCE_PREFLIGHT_STATUS),
        _expect("source_preflight_passed", decision.get("passed"), True),
        _expect("source_preflight_failed_checks", decision.get("failed_checks"), []),
        _expect("source_preflight_authorized_next_work", decision.get("authorized_next_work"), SOURCE_AUTHORIZED_NEXT_WORK),
        _expect("source_preflight_static_review_authorized", decision.get("evidence_package_static_review_authorized"), True),
        _expect("source_preflight_score_expression", decision.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_preflight_analysis_preflight_only", analysis.get("preflight_only"), True),
        _expect("source_preflight_analysis_promotion_executed", analysis.get("promotion_executed"), False),
        _expect("source_preflight_analysis_deployment_executed", analysis.get("deployment_executed"), False),
        _expect("source_preflight_analysis_training_execution", analysis.get("training_execution"), False),
        _expect("source_preflight_analysis_replay_execution", analysis.get("replay_execution"), False),
        _expect("source_preflight_analysis_candidate_generation", analysis.get("candidate_generation"), False),
        _expect("source_preflight_analysis_online_selector_change", analysis.get("online_selector_change"), False),
        _expect("source_preflight_analysis_dp_modification", analysis.get("dp_modification"), False),
        _expect("source_preflight_analysis_safety_claim", analysis.get("safety_or_camp_over_dp_claim"), False),
        _expect("source_summary_records", source_summary.get("records"), expected["records"]),
        _expect("source_summary_selection_logs", source_summary.get("selection_log_count"), expected["selection_log_count"]),
        _expect("source_summary_validation_summaries", source_summary.get("validation_summary_count"), expected["validation_summary_count"]),
        _expect("source_summary_replay_summaries", source_summary.get("replay_summary_count"), expected["replay_summary_count"]),
        _expect("source_summary_executed_top1", source_summary.get("executed_top1_records"), expected["executed_top1_records"]),
        _expect("source_summary_shadow_nonzero", source_summary.get("shadow_selected_index_nonzero_records"), expected["shadow_selected_index_nonzero_records"]),
        _expect("source_summary_feasible", source_summary.get("feasible_records"), expected["feasible_records"]),
        _expect("source_summary_fallback", source_summary.get("used_fallback_records"), expected["used_fallback_records"]),
        _expect("source_summary_selection_score_better", source_summary.get("selection_score_better_records"), expected["selection_score_better_records"]),
        _expect("source_summary_selection_score_tie", source_summary.get("selection_score_tie_records"), expected["selection_score_tie_records"]),
        _expect("source_summary_selection_score_worse", source_summary.get("selection_score_worse_records"), expected["selection_score_worse_records"]),
        _expect("source_summary_selection_score_uncomparable", source_summary.get("selection_score_uncomparable_records"), expected["selection_score_uncomparable_records"]),
        _expect("source_summary_training_records", source_summary.get("training_records"), expected["training_records"]),
        _expect("source_summary_dropped_records", source_summary.get("dropped_records_without_feasible_candidate"), expected["dropped_records_without_feasible_candidate"]),
        _expect("source_summary_num_candidates", source_summary.get("num_candidates"), expected["num_candidates"]),
        _expect("source_summary_num_atoms", source_summary.get("num_atoms"), expected["num_atoms"]),
        _expect("source_summary_runtime_manifest_schema", source_summary.get("runtime_manifest_schema_version"), SOURCE_RUNTIME_MANIFEST_SCHEMA),
        _expect("source_summary_score_expression", source_summary.get("score_expression"), SCORE_EXPRESSION),
        _expect("static_contract_default_off", static_contract.get("default_off"), True),
        _expect("static_contract_fail_closed", static_contract.get("fail_closed"), True),
        _expect("static_contract_executed_output_policy", static_contract.get("executed_output_policy"), "dp_top1"),
        _expect("static_contract_score_expression", static_contract.get("score_expression"), SCORE_EXPRESSION),
        _expect("static_contract_simplex_master_convex", static_contract.get("simplex_master_convex"), True),
        _expect("static_contract_cvar_master_convex", static_contract.get("cvar_master_convex"), True),
        _expect("static_contract_l2_master_convex", static_contract.get("l2_master_convex"), True),
    ]
    for name in BLOCKED_ACTIONS:
        checks.append(_expect(f"source_preflight_decision_{name}", decision.get(name), False))
        checks.append(_expect(f"source_preflight_blocked_{name}", blocked.get(name), False))
    return checks


def _artifact_manifest_checks(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    manifest = _list(preflight.get("artifact_manifest"))
    source_hashes = _dict(preflight.get("source_hashes"))
    by_name = {item.get("name"): item for item in manifest if isinstance(item, dict)}
    checks = [
        _expect("artifact_manifest_names", sorted(by_name), sorted(EXPECTED_ARTIFACT_NAMES)),
        _expect("source_hash_names", sorted(source_hashes), sorted(EXPECTED_ARTIFACT_NAMES)),
    ]
    for name in EXPECTED_ARTIFACT_NAMES:
        item = _dict(by_name.get(name))
        path = Path(str(item.get("path", "")))
        expected_sha = item.get("sha256")
        observed_sha = _sha256(path) if path.is_file() else None
        checks.extend(
            [
                _check(f"artifact_{name}_path_present", bool(item.get("path")), item.get("path"), "path"),
                _check(f"artifact_{name}_sha256_present", _is_sha256(expected_sha), expected_sha, "sha256"),
                _expect(f"artifact_{name}_source_hash_matches_manifest", source_hashes.get(name), expected_sha),
                _check(f"artifact_{name}_file_exists", path.is_file(), str(path), "file"),
                _expect(f"artifact_{name}_hash_matches_file", observed_sha, expected_sha),
            ]
        )
    return checks


def _preflight_file_hash_checks(
    preflight_json: Path,
    preflight_md: Path,
    sha256sums: dict[str, str],
) -> list[dict[str, Any]]:
    json_sha = _sha256(preflight_json) if preflight_json.is_file() else None
    md_sha = _sha256(preflight_md) if preflight_md.is_file() else None
    return [
        _expect(
            "source_preflight_sha256s_json_hash",
            sha256sums.get(preflight_json.name),
            json_sha,
        ),
        _expect(
            "source_preflight_sha256s_md_hash",
            sha256sums.get(preflight_md.name),
            md_sha,
        ),
    ]


def _source_surface_checks(script: str, test: str) -> list[dict[str, Any]]:
    return [
        _contains("source_surface_script_schema", script, "SCHEMA_VERSION"),
        _contains("source_surface_script_ready_status", script, "promotion_evidence_package_preflight_ready"),
        _contains_all(
            "source_surface_script_authorizes_static_review_only",
            script,
            ("AUTHORIZED_NEXT_WORK", "promotion_evidence_package_static_review_only"),
        ),
        _contains("source_surface_script_affine_score", script, SCORE_EXPRESSION),
        _contains("source_surface_script_blocks_promotion", script, '"promotion_executed": False'),
        _contains("source_surface_script_blocks_deployment", script, '"deployment_executed": False'),
        _contains("source_surface_script_blocks_training", script, '"training_execution": False'),
        _contains("source_surface_script_blocks_replay", script, '"replay_execution": False'),
        _contains("source_surface_script_blocks_candidate_generation", script, '"candidate_generation": False'),
        _contains("source_surface_script_blocks_dp_modification", script, '"dp_modification": False'),
        _contains("source_surface_script_blocks_safety_claim", script, '"safety_or_camp_over_dp_claim": False'),
        _contains("source_surface_script_checks_static_objective_delta", script, "selection_score_worse_records"),
        _contains("source_surface_test_pass_case", test, "test_runtime_promotion_evidence_package_preflight_passes"),
        _contains("source_surface_test_requires_enable", test, "test_runtime_promotion_evidence_package_preflight_requires_enable"),
        _contains("source_surface_test_rejects_wrong_eof", test, "test_runtime_promotion_evidence_package_preflight_rejects_wrong_eof"),
        _contains("source_surface_test_rejects_delta_worse", test, "test_runtime_promotion_evidence_package_preflight_rejects_delta_worse_records"),
        _contains("source_surface_test_rejects_promotion_leak", test, "test_runtime_promotion_evidence_package_preflight_rejects_promotion_authorization"),
    ]


def _audit_contract_checks(
    v14_text: str,
    status_text: str,
    *,
    rerun_after_user_authorization: bool = False,
) -> list[dict[str, Any]]:
    eof = _latest_text_block(v14_text)
    audit_pending = (
        f"current_v14_status={SOURCE_PREFLIGHT_STATUS}" in eof
        and f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in eof
    )
    audit_rerun_decision = (
        f"current_v14_status={REJECT_STATUS}" in eof
        and f"next_work_target={SOURCE_RERUN_DECISION_NEXT_WORK}" in eof
    )
    audit_complete = (
        f"current_v14_status={READY_STATUS}" in eof
        and f"next_work_target={AUTHORIZED_NEXT_WORK}" in eof
    )
    status_pending = (
        f"current_v14_status={SOURCE_PREFLIGHT_STATUS}" in status_text
        and f"next_work_target={SOURCE_AUTHORIZED_NEXT_WORK}" in status_text
    )
    status_rerun_decision = (
        f"current_v14_status={REJECT_STATUS}" in status_text
        and f"next_work_target={SOURCE_RERUN_DECISION_NEXT_WORK}" in status_text
    )
    status_complete = (
        f"current_v14_status={READY_STATUS}" in status_text
        and f"next_work_target={AUTHORIZED_NEXT_WORK}" in status_text
    )
    audit_boundary_ok = audit_pending or audit_complete or (
        rerun_after_user_authorization and audit_rerun_decision
    )
    status_boundary_ok = status_pending or status_complete or (
        rerun_after_user_authorization and status_rerun_decision
    )
    return [
        _expect(
            "audit_rerun_requires_explicit_user_authorization_flag",
            (not audit_rerun_decision) or rerun_after_user_authorization,
            True,
        ),
        _check(
            "audit_latest_boundary_matches_static_review_gate",
            audit_boundary_ok,
            {
                "status": _extract_line(eof, "current_v14_status="),
                "next": _extract_line(eof, "next_work_target="),
                "rerun_after_user_authorization": rerun_after_user_authorization,
            },
            "pending static review, completed static review, or explicitly authorized rerun decision",
        ),
        _check(
            "current_status_boundary_matches_static_review_gate",
            status_boundary_ok,
            {
                "pending": status_pending,
                "complete": status_complete,
                "rerun_decision": status_rerun_decision,
                "rerun_after_user_authorization": rerun_after_user_authorization,
            },
            "pending static review, completed static review, or explicitly authorized rerun decision",
        ),
        _check(
            "audit_records_preflight_ready",
            (
                "default_off_shadow_selector_runtime_promotion_evidence_package_preflight_ready=True"
                in eof
            )
            or (
                rerun_after_user_authorization
                and "default_off_shadow_selector_runtime_promotion_evidence_package_static_review_failed=True"
                in eof
            ),
            "preflight ready marker or authorized rerun failure marker present",
            "preflight ready marker, or failed static review marker for explicit rerun",
        ),
        _check(
            "audit_authorizes_static_review",
            (
                "default_off_shadow_selector_runtime_promotion_evidence_package_static_review_authorized=True"
                in eof
            )
            or (
                rerun_after_user_authorization
                and "default_off_shadow_selector_runtime_promotion_evidence_package_static_review_rerun_requires_user_decision=True"
                in eof
            ),
            "static review authorization marker or authorized rerun decision marker present",
            "static review authorization marker, or rerun decision marker with explicit user authorization",
        ),
        _contains("audit_blocks_runtime_execution", eof, "default_off_shadow_selector_runtime_execution_authorized=False"),
        _contains("audit_blocks_dp_modification", eof, "dp_modification_authorized_by_current_boundary=False"),
        _contains("audit_blocks_selector_promotion", eof, "selector_promotion_authorized=False"),
        _contains("audit_blocks_deployment", eof, "deployment_authorized=False"),
        _contains("audit_blocks_safety_claim", eof, "safety_benefit_claim_authorized=False"),
        _contains("audit_blocks_camp_over_dp_claim", eof, "camp_over_dp_top1_claim_authorized=False"),
    ]


def _source_preflight_summary(preflight: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(preflight.get("final_decision"))
    source_summary = _dict(preflight.get("source_summary"))
    manifest = _list(preflight.get("artifact_manifest"))
    return {
        "status": decision.get("status"),
        "passed": decision.get("passed"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "artifact_entries": ",".join(item.get("name", "") for item in manifest if isinstance(item, dict)),
        "records": source_summary.get("records"),
        "executed_top1_records": source_summary.get("executed_top1_records"),
        "shadow_selected_index_nonzero_records": source_summary.get("shadow_selected_index_nonzero_records"),
        "selection_score_better_records": source_summary.get("selection_score_better_records"),
        "selection_score_tie_records": source_summary.get("selection_score_tie_records"),
        "selection_score_worse_records": source_summary.get("selection_score_worse_records"),
        "selection_score_uncomparable_records": source_summary.get("selection_score_uncomparable_records"),
        "training_records": source_summary.get("training_records"),
        "dropped_records_without_feasible_candidate": source_summary.get("dropped_records_without_feasible_candidate"),
        "runtime_manifest_schema_version": source_summary.get("runtime_manifest_schema_version"),
        "score_expression": source_summary.get("score_expression"),
    }


def _artifact_manifest_review(preflight: dict[str, Any]) -> list[dict[str, Any]]:
    review: list[dict[str, Any]] = []
    for item in _list(preflight.get("artifact_manifest")):
        if not isinstance(item, dict):
            continue
        path = Path(str(item.get("path", "")))
        expected_sha = item.get("sha256")
        observed_sha = _sha256(path) if path.is_file() else None
        review.append(
            {
                "name": item.get("name"),
                "path": str(path),
                "exists": path.is_file(),
                "sha256": expected_sha,
                "observed_sha256": observed_sha,
                "hash_matches": observed_sha == expected_sha,
            }
        )
    return review


def _review_scope() -> list[str]:
    return [
        "verify the evidence-package preflight artifact and SHA256SUMS",
        "verify all nine source artifacts named by the preflight still hash-match",
        "verify the source boundary remains default-off, fail-closed, and DP Top-1 executed",
        "verify CAMP remains affine score_k(w)=a_k^T w over approved atoms with nonnegative simplex weights",
        "verify selector promotion, deployment, DP modification, replay, training, candidate generation, and safety claims remain unauthorized",
    ]


def _forbidden_paths() -> list[str]:
    return [
        "promoting the selector or atoms",
        "deploying or claiming a deployable checkpoint",
        "changing executed trajectory selection away from DP Top-1",
        "running replay, training, or candidate generation in this review",
        "generating, modifying, blending, guiding, or postprocessing trajectories",
        "modifying TiERIV Diffusion Planner code, config, weights, or checkpoint",
        "claiming safety benefit or CAMP superiority over DP Top-1",
    ]


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": failed,
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": SOURCE_AUTHORIZED_NEXT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "runtime_promotion_evidence_package_static_review_passed": bool(passed),
        "evidence_package_construction_authorized": bool(passed),
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
    if "static_review_enabled" in failed_set:
        return "explicit_static_review_authorization_missing"
    if {"current_dp_head_fixed", "required_dp_head_fixed"} & failed_set:
        return "fixed_dp_contract_failure"
    if any(name.startswith("audit_") or name.startswith("current_status_") for name in failed):
        return "v14_eof_contract_mismatch"
    if any(name.startswith("source_preflight_sha256s_") for name in failed):
        return "source_preflight_sha256s_mismatch"
    if any(name.startswith("artifact_") for name in failed) or "artifact_manifest_names" in failed_set:
        return "source_artifact_hash_mismatch"
    if any(name.startswith("source_surface_") for name in failed):
        return "source_surface_contract_failure"
    if any(name.startswith("source_preflight_") or name.startswith("source_summary_") or name.startswith("static_contract_") for name in failed):
        return "source_preflight_contract_failure"
    if any(name.endswith("_exists") or name.endswith("_nonempty") for name in failed):
        return "source_file_missing_or_empty"
    return "runtime_promotion_evidence_package_static_review_contract_failure"


def _file_checks(name: str, path: Path) -> list[dict[str, Any]]:
    return [
        _check(f"{name}_exists", path.is_file(), str(path), "file"),
        _check(
            f"{name}_nonempty",
            path.is_file() and path.stat().st_size > 0,
            path.stat().st_size if path.is_file() else None,
            ">0 bytes",
        ),
    ]


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": _stable(observed),
        "expected": _stable(expected),
    }


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _contains_all(name: str, text: str, needles: tuple[str, ...]) -> dict[str, Any]:
    missing = [needle for needle in needles if needle not in text]
    return _check(name, not missing, missing or "all present", list(needles))


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _read_sha256sums(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            rows[Path(parts[1].strip()).name] = parts[0]
    return rows


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    rows: list[str] = []
    for path in sorted(output_dir.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name != "SHA256SUMS":
            rows.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    return text if len(text) <= 120 else text[:117] + "..."


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _latest_text_block(text: str) -> str:
    marker = "\n## "
    index = text.rfind(marker)
    return text[index + 1 :] if index >= 0 else text


def _extract_line(text: str, prefix: str) -> str | None:
    matches = [line for line in text.splitlines() if line.startswith(prefix)]
    return matches[-1] if matches else None


if __name__ == "__main__":
    raise SystemExit(main())
