#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_v1"
)
DISABLED_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_default_off_disabled"
)
READY_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_rejected"
)
SOURCE_REVIEW_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review_complete"
)
SOURCE_AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_static_contract_review_only"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
RUNTIME_MANIFEST_SCHEMA_VERSION = "dp_camp_v13_default_off_shadow_selector_runtime_v1"
ATOM_SCHEMA_VERSION = "dp_camp_v10_14d"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 14

BLOCKED_ACTIONS = (
    "artifact_manifest_materialization_authorized",
    "default_off_shadow_selector_runtime_execution_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "replay_execution_authorized",
    "candidate_generation_authorized",
    "dp_modification_authorized",
    "online_selector_change_authorized",
    "production_selector_change_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan-only gate for future materialization of the v13 default-off "
            "shadow selector runtime artifact manifest. This designs the "
            "manifest content and static-review requirements, but it does not "
            "write the runtime manifest, execute replay, enable the shadow "
            "selector, train CAMP, generate candidates, modify DP, promote, "
            "deploy, or authorize safety/CAMP-over-DP claims."
        )
    )
    parser.add_argument("--artifact_manifest_static_contract_review_json", type=Path, required=True)
    parser.add_argument("--artifact_manifest_plan_json", type=Path, required=True)
    parser.add_argument("--replay_runner_py", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--planned_runtime_manifest_path", required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--enable_v13_default_off_shadow_selector_artifact_manifest_materialization_plan",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        artifact_manifest_static_contract_review_json=args.artifact_manifest_static_contract_review_json,
        artifact_manifest_plan_json=args.artifact_manifest_plan_json,
        replay_runner_py=args.replay_runner_py,
        v13_audit_md=args.v13_audit_md,
        planned_runtime_manifest_path=args.planned_runtime_manifest_path,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v13_default_off_shadow_selector_artifact_manifest_materialization_plan
        ),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 1 if report["final_decision"]["status"] == REJECT_STATUS else 0


def build_report(
    *,
    artifact_manifest_static_contract_review_json: Path,
    artifact_manifest_plan_json: Path,
    replay_runner_py: Path,
    v13_audit_md: Path,
    planned_runtime_manifest_path: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    label: str | None = None,
    enabled: bool = False,
) -> dict[str, Any]:
    report = _empty_report(
        enabled=enabled,
        label=label,
        planned_runtime_manifest_path=planned_runtime_manifest_path,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
    )
    if not enabled:
        return report

    paths = {
        "artifact_manifest_static_contract_review": artifact_manifest_static_contract_review_json,
        "artifact_manifest_plan": artifact_manifest_plan_json,
        "replay_runner": replay_runner_py,
        "v13_audit": v13_audit_md,
    }
    checks: list[dict[str, Any]] = [
        _check(
            "current_camp_head_is_sha",
            _is_git_sha(current_camp_head),
            current_camp_head,
            "40-char git sha",
        ),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check(
            "planned_runtime_manifest_path_is_json",
            planned_runtime_manifest_path.endswith(".json"),
            planned_runtime_manifest_path,
            "*.json",
        ),
    ]
    payloads: dict[str, Any] = {}
    texts: dict[str, str] = {}
    for name, path in paths.items():
        checks.append(_check(f"{name}_exists", path.is_file(), str(path), "existing file"))
        if not path.is_file():
            continue
        report["source_hashes"][f"{name}_sha256"] = _sha256(path)
        if path.suffix == ".json":
            loaded, json_check = _load_json(path, name)
            payloads[name] = loaded
            checks.append(json_check)
        else:
            texts[name] = path.read_text(encoding="utf-8")

    source_review = _dict(payloads.get("artifact_manifest_static_contract_review"))
    source_plan = _dict(payloads.get("artifact_manifest_plan"))
    checks.extend(_source_review_checks(source_review))
    checks.extend(_source_plan_checks(source_plan))
    checks.extend(_source_surface_checks(texts))
    passed = all(check["passed"] for check in checks)

    report["source_summary"] = _source_summary(source_review, source_plan, report["source_hashes"])
    report["materialization_plan"] = _materialization_plan(
        source_plan=source_plan,
        planned_runtime_manifest_path=planned_runtime_manifest_path,
        source_hashes=report["source_hashes"],
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
    )
    report["future_static_review_requirements"] = _future_static_review_requirements()
    report["forbidden_paths"] = _forbidden_paths()
    report["plan_checks"] = checks
    report["final_decision"] = _decision(passed, checks)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report.get("materialization_plan", {})
    lines = [
        "# DP-CAMP V13 Default-Off Shadow Selector Artifact Manifest Materialization Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Materialization static review authorized: `{decision['artifact_manifest_materialization_static_contract_review_authorized']}`",
        f"- Manifest materialization authorized: `{decision['artifact_manifest_materialization_authorized']}`",
        f"- Shadow runtime execution authorized: `{decision['default_off_shadow_selector_runtime_execution_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Materialization Plan",
        "",
        f"- Status: `{plan.get('status')}`",
        f"- Planned runtime manifest path: `{plan.get('planned_runtime_manifest_path')}`",
        f"- Runtime manifest written by this gate: `{plan.get('runtime_manifest_written_by_this_gate')}`",
        f"- This plan is runtime manifest: `{plan.get('this_plan_is_runtime_manifest')}`",
        f"- Runtime schema: `{plan.get('future_manifest_required_content', {}).get('schema_version')}`",
        "",
        "## Required Runtime Entries",
        "",
    ]
    entries = plan.get("future_manifest_required_content", {}).get("artifacts", {})
    if isinstance(entries, dict):
        for name, entry in entries.items():
            if not isinstance(entry, dict):
                continue
            lines.append(
                f"- `{name}` path=`{entry.get('path')}` sha256=`{entry.get('sha256')}`"
            )
    lines.extend(["", "## Future Static Review Requirements", ""])
    for item in report.get("future_static_review_requirements", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Forbidden Paths", ""])
    for item in report.get("forbidden_paths", []):
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "This gate is plan-only. It does not write the runtime manifest, "
            "execute replay, enable the shadow selector, train CAMP, generate "
            "candidates, modify DP, promote atoms or selectors, deploy, or "
            "authorize safety/CAMP-over-DP claims.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report.get("plan_checks", []):
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _empty_report(
    *,
    enabled: bool,
    label: str | None,
    planned_runtime_manifest_path: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "name": (
                "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan"
            ),
            "label": label,
            "default_off": True,
            "enabled": bool(enabled),
            "plan_only": True,
            "artifact_manifest_materialized": False,
            "runtime_execution": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_generation_execution": False,
            "dp_modification_execution": False,
            "planned_runtime_manifest_path": planned_runtime_manifest_path,
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "math_boundary": (
                "Future runtime manifest materialization must only preserve "
                "immutable paths and hashes for fixed-DP-candidate reranking. "
                "It must not alter candidates, scores, weights, DP, selector "
                "routing, or runtime behavior."
            ),
        },
        "source_hashes": {},
        "source_summary": {},
        "materialization_plan": {},
        "future_static_review_requirements": [],
        "forbidden_paths": [],
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "plan_checks": [],
        "final_decision": {
            "status": DISABLED_STATUS,
            "passed": False,
            "enabled": False,
            "authorized_next_work": None,
            "artifact_manifest_materialization_plan_ready": False,
            "artifact_manifest_materialization_static_contract_review_authorized": False,
            "artifact_manifest_materialization_authorized": False,
            "default_off_shadow_selector_runtime_execution_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "production_selector_change_authorized": False,
            "training_authorization_changed_by_plan": False,
            "training_executed": False,
            "failed_checks": [],
        },
    }


def _source_review_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    return [
        _expect("source_review_schema_version", payload.get("schema_version"), "dp_camp_v13_default_off_shadow_selector_artifact_manifest_static_contract_review_v1"),
        _expect("source_review_status_complete", decision.get("status"), SOURCE_REVIEW_STATUS),
        _expect("source_review_passed", decision.get("passed"), True),
        _expect("source_review_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_review_authorizes_this_plan", decision.get("authorized_next_work"), SOURCE_AUTHORIZED_NEXT_WORK),
        _expect("source_review_complete_flag", decision.get("artifact_manifest_static_contract_review_complete"), True),
        _expect("source_review_materialization_plan_authorized", decision.get("artifact_manifest_materialization_plan_authorized"), True),
        _expect("source_review_materialization_forbidden", decision.get("artifact_manifest_materialization_authorized"), False),
        _expect("source_review_runtime_forbidden", decision.get("default_off_shadow_selector_runtime_execution_authorized"), False),
        _expect("source_review_replay_forbidden", decision.get("replay_execution_authorized"), False),
        _expect("source_review_candidate_generation_forbidden", decision.get("candidate_generation_authorized"), False),
        _expect("source_review_dp_modification_forbidden", decision.get("dp_modification_authorized"), False),
        _expect("source_review_training_not_executed", decision.get("training_executed"), False),
        *[
            _expect(f"source_review_{name}_false", decision.get(name), False)
            for name in BLOCKED_ACTIONS
        ],
    ]


def _source_plan_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("artifact_manifest_plan"))
    runtime_entries = _dict(plan.get("required_runtime_entries"))
    evidence_entries = _dict(plan.get("required_evidence_entries"))
    atom_entry = _dict(runtime_entries.get("atom_scales"))
    weights_entry = _dict(runtime_entries.get("static_weights"))
    return [
        _expect("source_plan_status", decision.get("status"), "dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_ready"),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_plan_materialization_forbidden", decision.get("artifact_manifest_materialization_authorized"), False),
        _expect("source_plan_runtime_forbidden", decision.get("default_off_shadow_selector_runtime_execution_authorized"), False),
        _expect("source_plan_status_no_manifest_written", plan.get("status"), "plan_ready_no_runtime_manifest_materialized"),
        _expect("source_plan_runtime_schema", plan.get("runtime_manifest_schema_version"), RUNTIME_MANIFEST_SCHEMA_VERSION),
        _expect("source_plan_materialized_by_this_gate_false", plan.get("materialized_by_this_gate"), False),
        _expect("source_plan_selector_mode_static", plan.get("selector_mode"), "static"),
        _expect("source_plan_candidate_count", plan.get("candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("source_plan_atom_count", plan.get("atom_count"), EXPECTED_ATOM_COUNT),
        _expect("source_plan_atom_schema", plan.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("source_plan_score_expression", plan.get("score_expression"), SCORE_EXPRESSION),
        _expect("source_plan_atom_scales_logical_name", atom_entry.get("logical_name"), "atom_scales"),
        _check("source_plan_atom_scales_path_present", bool(atom_entry.get("path")), atom_entry.get("path"), "nonempty path"),
        _check("source_plan_atom_scales_sha256", _is_sha256(atom_entry.get("sha256")), atom_entry.get("sha256"), "sha256"),
        _expect("source_plan_static_weights_logical_name", weights_entry.get("logical_name"), "static_weights"),
        _check("source_plan_static_weights_path_present", bool(weights_entry.get("path")), weights_entry.get("path"), "nonempty path"),
        _check("source_plan_static_weights_sha256", _is_sha256(weights_entry.get("sha256")), weights_entry.get("sha256"), "sha256"),
        _check("source_plan_has_training_summary_evidence", "training_summary" in evidence_entries, list(evidence_entries), "training_summary"),
        _check("source_plan_has_fallback_master_evidence", "fallback_master_config" in evidence_entries, list(evidence_entries), "fallback_master_config"),
        _contains_in_list(
            "source_plan_future_manifest_placeholder",
            plan.get("planned_runner_args"),
            "--camp_shadow_artifact_manifest <future_runtime_manifest_json>",
        ),
    ]


def _source_surface_checks(texts: dict[str, str]) -> list[dict[str, Any]]:
    runner = texts.get("replay_runner", "")
    audit = texts.get("v13_audit", "")
    return [
        _contains("runner_manifest_loader_present", runner, "def _load_shadow_artifact_manifest"),
        _contains("runner_manifest_expected_sha_lookup_present", runner, "def _manifest_expected_sha256"),
        _contains("runner_manifest_artifacts_lookup", runner, 'artifacts = manifest.get("artifacts")'),
        _contains("runner_manifest_sha256_lookup", runner, 'hashes = manifest.get("sha256")'),
        _contains("runner_atom_scales_logical_name", runner, 'logical_name="atom_scales"'),
        _contains("runner_static_weights_logical_name", runner, 'logical_name="static_weights"'),
        _contains("runner_hash_mismatch_fails_closed", runner, "hash_mismatch"),
        _contains(
            "audit_current_scope_authorizes_materialization_plan_only",
            audit,
            "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_only",
        ),
        _contains("audit_materialization_still_blocked", audit, "artifact_manifest_materialization_authorized=False"),
        _contains("audit_runtime_still_blocked", audit, "runtime_shadow_selector_execution_authorized=False"),
        _contains("audit_training_authorization_preserved", audit, "current_v13_all_subsequent_training_tasks_authorized_by_user=True"),
    ]


def _source_summary(
    source_review: dict[str, Any],
    source_plan: dict[str, Any],
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    review_decision = _dict(source_review.get("final_decision"))
    plan_decision = _dict(source_plan.get("final_decision"))
    plan = _dict(source_plan.get("artifact_manifest_plan"))
    return {
        "source_hashes": source_hashes,
        "source_review_status": review_decision.get("status"),
        "source_review_passed": review_decision.get("passed"),
        "source_review_authorized_next_work": review_decision.get("authorized_next_work"),
        "source_plan_status": plan_decision.get("status"),
        "source_plan_passed": plan_decision.get("passed"),
        "runtime_manifest_schema_version": plan.get("runtime_manifest_schema_version"),
        "required_runtime_entries": sorted(_dict(plan.get("required_runtime_entries"))),
        "required_evidence_entries": sorted(_dict(plan.get("required_evidence_entries"))),
    }


def _materialization_plan(
    *,
    source_plan: dict[str, Any],
    planned_runtime_manifest_path: str,
    source_hashes: dict[str, str],
    current_camp_head: str,
    current_dp_head: str,
) -> dict[str, Any]:
    plan = _dict(source_plan.get("artifact_manifest_plan"))
    runtime_entries = _dict(plan.get("required_runtime_entries"))
    evidence_entries = _dict(plan.get("required_evidence_entries"))
    atom_entry = _dict(runtime_entries.get("atom_scales"))
    weights_entry = _dict(runtime_entries.get("static_weights"))
    atom_path = str(atom_entry.get("path"))
    weights_path = str(weights_entry.get("path"))
    atom_sha = atom_entry.get("sha256")
    weights_sha = weights_entry.get("sha256")
    aliases = {
        "atom_scales": atom_sha,
        atom_path: atom_sha,
        Path(atom_path).name: atom_sha,
        "static_weights": weights_sha,
        weights_path: weights_sha,
        Path(weights_path).name: weights_sha,
    }
    return {
        "status": "plan_ready_no_runtime_manifest_written",
        "planned_runtime_manifest_path": planned_runtime_manifest_path,
        "this_plan_is_runtime_manifest": False,
        "runtime_manifest_written_by_this_gate": False,
        "runtime_execution_enabled_by_this_gate": False,
        "future_manifest_required_content": {
            "schema_version": RUNTIME_MANIFEST_SCHEMA_VERSION,
            "manifest_role": "default_off_shadow_selector_runtime_artifact_manifest",
            "default_off": True,
            "selection_effect": False,
            "selector_mode": "static",
            "candidate_operation": "fixed DP candidate reranking only",
            "executed_output_policy": "dp_top1",
            "required_candidate_count": EXPECTED_CANDIDATE_COUNT,
            "atom_count": EXPECTED_ATOM_COUNT,
            "atom_schema_version": ATOM_SCHEMA_VERSION,
            "score_expression": SCORE_EXPRESSION,
            "camp_head_at_plan": current_camp_head,
            "required_dp_head": FIXED_DP_HEAD,
            "dp_head_at_plan": current_dp_head,
            "artifacts": {
                "atom_scales": {
                    "logical_name": "atom_scales",
                    "path": atom_path,
                    "sha256": atom_sha,
                    "required": True,
                },
                "static_weights": {
                    "logical_name": "static_weights",
                    "path": weights_path,
                    "sha256": weights_sha,
                    "required": True,
                },
            },
            "sha256": aliases,
            "evidence": evidence_entries,
            "source_plan_sha256": source_hashes.get("artifact_manifest_plan_sha256"),
            "source_static_review_sha256": source_hashes.get(
                "artifact_manifest_static_contract_review_sha256"
            ),
            "forbidden_runtime_claims": {
                "selector_promotion_authorized": False,
                "atom_promotion_authorized": False,
                "deployment_authorized": False,
                "safety_benefit_claim_authorized": False,
                "camp_over_dp_top1_claim_authorized": False,
            },
        },
        "future_materializer_preconditions": [
            "run only after materialization implementation plan, static review, and unit tests pass",
            "write exactly one runtime manifest file at the planned path",
            "write atom_scales and static_weights entries with logical, absolute-path, and basename hash aliases",
            "verify atom scales and weights files exist and match planned sha256 before writing",
            "verify DP head remains fixed before writing",
            "do not execute replay or enable the shadow selector while writing the manifest",
        ],
        "future_runtime_invocation_template": [
            "--camp_selector_mode static",
            f"--num_candidates {EXPECTED_CANDIDATE_COUNT}",
            "--camp_default_off_shadow_selector",
            f"--camp_atom_scales {atom_path}",
            f"--camp_static_weights {weights_path}",
            f"--camp_shadow_artifact_manifest {planned_runtime_manifest_path}",
            f"--camp_shadow_expected_atom_scales_sha256 {atom_sha}",
            f"--camp_shadow_expected_static_weights_sha256 {weights_sha}",
        ],
    }


def _future_static_review_requirements() -> list[str]:
    return [
        "prove the materialization plan output is not itself a runtime manifest",
        "prove no runtime manifest file was written by the plan-only gate",
        "prove future manifest content has schema dp_camp_v13_default_off_shadow_selector_runtime_v1",
        "prove future manifest includes atom_scales and static_weights logical entries and sha256 aliases",
        "prove future manifest preserves fixed DP K=8, 14 atoms, simplex affine score boundary, and DP Top-1 execution policy",
        "prove future materialization still does not execute replay, train CAMP, modify DP, promote, deploy, or claim safety benefit",
    ]


def _forbidden_paths() -> list[str]:
    return [
        "writing the runtime manifest in this plan-only gate",
        "using this plan JSON as --camp_shadow_artifact_manifest",
        "running replay with the planned manifest path",
        "enabling the shadow selector runtime",
        "training CAMP or changing weights during manifest planning",
        "modifying, retraining, or tuning Diffusion Planner",
        "promoting atoms, selectors, deployment artifacts, or safety claims",
    ]


def _decision(passed: bool, checks: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "enabled": True,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "artifact_manifest_materialization_plan_ready": bool(passed),
        "artifact_manifest_materialization_static_contract_review_authorized": bool(passed),
        "artifact_manifest_materialization_authorized": False,
        "default_off_shadow_selector_runtime_execution_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "replay_execution_authorized": False,
        "candidate_generation_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "production_selector_change_authorized": False,
        "training_authorization_changed_by_plan": False,
        "training_executed": False,
        "failed_checks": failed,
    }


def _load_json(path: Path, name: str) -> tuple[Any, dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, _check(f"{name}_valid_json", False, type(exc).__name__, "valid JSON")
    return payload, _check(f"{name}_json_object", isinstance(payload, dict), type(payload).__name__, "dict")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _contains_in_list(name: str, values: Any, needle: str) -> dict[str, Any]:
    if not isinstance(values, list):
        return _check(name, False, type(values).__name__, f"list containing {needle}")
    matched = [value for value in values if isinstance(value, str) and needle in value]
    return _check(name, bool(matched), matched or "missing", f"contains {needle}")


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": _stable(observed),
        "expected": _stable(expected),
    }


def _stable(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    return value


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        ch in "0123456789abcdef" for ch in value.lower()
    )


if __name__ == "__main__":
    raise SystemExit(main())
