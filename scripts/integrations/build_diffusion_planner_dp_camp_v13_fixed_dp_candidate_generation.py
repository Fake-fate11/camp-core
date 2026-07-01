#!/usr/bin/env python3
"""Fail-closed builder for v13 fixed-DP candidate generation artifacts.

The builder emits a guarded runbook and manifest for a future fixed Diffusion
Planner candidate-generation execution gate. It does not run Diffusion Planner,
generate candidates, prepare data, replay, train CAMP, modify DP, promote,
deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SOURCE_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v13_fixed_dp_candidate_generation_implementation_static_contract_review_v1"
)
SOURCE_REVIEW_PASS_STATUS = (
    "dp_camp_v13_fixed_dp_candidate_generation_implementation_static_contract_review_passed"
)
SCHEMA_VERSION = "dp_camp_v13_fixed_dp_candidate_generation_builder_v1"
READY_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_builder_complete"
REJECT_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_builder_rejected"
DISABLED_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_builder_default_off_disabled"
MANIFEST_SCHEMA_VERSION = "dp_camp_v13_fixed_dp_candidate_generation_manifest_v1"
RUNBOOK_SCHEMA_VERSION = "dp_camp_v13_fixed_dp_candidate_generation_runbook_v1"
LATEST_AUDIT_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_implementation_static_contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_implementation_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_evaluation_executed_index_contract_"
    "failure_remediation_fixed_dp_candidate_generation_post_implementation_static_contract_review_only"
)
GUARD_ENV_VAR = "DP_CAMP_V13_FIXED_DP_CANDIDATE_GENERATION_EXECUTE"
TARGET_MIN_CANDIDATE_MEMBERS = 1024
TARGET_CANDIDATES_PER_MEMBER = 8
OUTPUT_FILES = (
    "fixed_dp_candidate_generation_manifest.json",
    "run_fixed_dp_candidate_generation.sh",
    "candidate_tensor_hash_registry_template.json",
    "path_signature_registry_template.json",
    "record_identity_registry_template.json",
    "split_manifest_root_registry_template.json",
    "zero_overlap_preflight_inputs_template.json",
)
ZERO_OVERLAP_KEYS = (
    "candidate_tensor_hash",
    "path_signature",
    "record_identity",
    "split_manifest_root",
)
FORMAL_SEEDS = {11, 12, 13}
SOURCE_FALSE_FLAGS = (
    "fixed_dp_candidate_generation_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "candidate_generation_by_camp_authorized",
    "trajectory_generation_by_camp_authorized",
    "trajectory_modification_by_camp_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "data_preparation_authorized_next",
    "replay_execution_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_next",
    "dp_modification_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)
AUDIT_FALSE_FLAGS = (
    "fixed_dp_candidate_generation_authorized_next",
    "fixed_dp_candidate_generation_execution_authorized_next",
    "fresh_member_source_materialization_execution_authorized_next",
    "fresh_evaluation_split_evaluation_execution_authorized_next",
    "fresh_evaluation_split_evaluation_result_review_authorized_next",
    "data_preparation_authorized_next",
    "training_preflight_authorized_next",
    "training_execution_authorized_by_current_boundary",
    "runtime_shadow_selector_execution_authorized",
    "replay_execution_authorized_by_current_boundary",
    "fixed_dp_candidate_generation_authorized_by_current_boundary",
    "candidate_generation_by_camp_authorized_by_current_boundary",
    "trajectory_generation_by_camp_authorized_by_current_boundary",
    "trajectory_modification_by_camp_authorized_by_current_boundary",
    "dp_modification_authorized_by_current_boundary",
    "formal_seed_11_12_13_execution_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_or_postselection_authorized",
    "closed_loop_outcome_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation_static_contract_review_json", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--dp_repo", default="/root/autodl-tmp/Diffusion-Planner")
    parser.add_argument("--camp_repo", default="/root/autodl-tmp/camp_core")
    parser.add_argument("--dp_entrypoint", default="tools/camp_fixed_candidate_generation.py")
    parser.add_argument("--target_min_candidate_members", type=int, default=TARGET_MIN_CANDIDATE_MEMBERS)
    parser.add_argument("--target_candidates_per_member", type=int, default=TARGET_CANDIDATES_PER_MEMBER)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument("--enable_fixed_dp_candidate_generation_builder", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_generation_report(
        implementation_static_contract_review_json=args.implementation_static_contract_review_json,
        v13_audit_md=args.v13_audit_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        dp_repo=args.dp_repo,
        camp_repo=args.camp_repo,
        dp_entrypoint=args.dp_entrypoint,
        target_min_candidate_members=args.target_min_candidate_members,
        target_candidates_per_member=args.target_candidates_per_member,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
        enabled=args.enable_fixed_dp_candidate_generation_builder,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_generation_report(
    *,
    implementation_static_contract_review_json: Path,
    v13_audit_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    dp_repo: str = "/root/autodl-tmp/Diffusion-Planner",
    camp_repo: str = "/root/autodl-tmp/camp_core",
    dp_entrypoint: str = "tools/camp_fixed_candidate_generation.py",
    target_min_candidate_members: int = TARGET_MIN_CANDIDATE_MEMBERS,
    target_candidates_per_member: int = TARGET_CANDIDATES_PER_MEMBER,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    enabled: bool = False,
) -> dict[str, Any]:
    source_review = _load_json_dict(implementation_static_contract_review_json)
    source_decision = _dict(source_review.get("final_decision"))
    review_contract = _dict(source_review.get("review_contract"))
    audit_text = _read_text(v13_audit_md)
    output_dir = output_dir.resolve()
    output_paths = _output_paths(output_dir)
    runbook = render_runbook(
        dp_repo=dp_repo,
        camp_repo=camp_repo,
        dp_entrypoint=dp_entrypoint,
        output_dir=str(output_dir),
        target_min_candidate_members=target_min_candidate_members,
        target_candidates_per_member=target_candidates_per_member,
        required_dp_head=required_dp_head,
    )
    checks = _checks(
        implementation_static_contract_review_json=implementation_static_contract_review_json,
        v13_audit_md=v13_audit_md,
        source_review=source_review,
        source_decision=source_decision,
        review_contract=review_contract,
        audit_text=audit_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        target_min_candidate_members=target_min_candidate_members,
        target_candidates_per_member=target_candidates_per_member,
        authorized_current_work=authorized_current_work,
        enabled=enabled,
        runbook=runbook,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    if passed:
        _write_outputs(
            output_paths=output_paths,
            runbook=runbook,
            dp_repo=dp_repo,
            camp_repo=camp_repo,
            dp_entrypoint=dp_entrypoint,
            target_min_candidate_members=target_min_candidate_members,
            target_candidates_per_member=target_candidates_per_member,
            required_dp_head=required_dp_head,
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "implementation_only": True,
            "fixed_dp_candidate_generation_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "data_preparation_execution": False,
            "replay_execution": False,
            "training_preflight": False,
            "training_execution": False,
            "dp_modification": False,
            "promotion": False,
            "deployment": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "generation_builder": {
            "builder_enabled": enabled,
            "manifest_written": passed,
            "fixed_dp_candidate_generation_executed": False,
            "runbook_guard_env_var": GUARD_ENV_VAR,
            "target_min_candidate_members": target_min_candidate_members,
            "target_candidates_per_member": target_candidates_per_member,
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
            "output_files": list(OUTPUT_FILES),
        },
        "output_paths": {key: str(value) for key, value in output_paths.items()},
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            enabled=enabled,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def render_runbook(
    *,
    dp_repo: str,
    camp_repo: str,
    dp_entrypoint: str,
    output_dir: str,
    target_min_candidate_members: int,
    target_candidates_per_member: int,
    required_dp_head: str,
) -> str:
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            f": \"${{{GUARD_ENV_VAR}:-}}\"",
            f"if [ \"${{{GUARD_ENV_VAR}:-}}\" != \"1\" ]; then",
            f"  echo \"Refusing to run: set {GUARD_ENV_VAR}=1 in an authorized execution gate\" >&2",
            "  exit 40",
            "fi",
            "",
            "source /etc/network_turbo >/dev/null 2>&1 || true",
            f"DP_REPO={_shell_quote(dp_repo)}",
            f"CAMP_REPO={_shell_quote(camp_repo)}",
            f"OUT_DIR={_shell_quote(output_dir)}",
            f"REQUIRED_DP_HEAD={_shell_quote(required_dp_head)}",
            "ACTUAL_DP_HEAD=$(git -C \"$DP_REPO\" rev-parse HEAD)",
            "if [ \"$ACTUAL_DP_HEAD\" != \"$REQUIRED_DP_HEAD\" ]; then",
            "  echo \"DP HEAD mismatch: $ACTUAL_DP_HEAD\" >&2",
            "  exit 41",
            "fi",
            "",
            "mkdir -p \"$OUT_DIR\"",
            "# The entrypoint must emit fixed DP candidate tensors and registries only.",
            "python " + _shell_quote(f"{dp_repo}/{dp_entrypoint}") + " \\",
            f"  --output_dir \"$OUT_DIR\" \\",
            f"  --target_min_candidate_members {target_min_candidate_members} \\",
            f"  --target_candidates_per_member {target_candidates_per_member} \\",
            "  --forbid_full36 \\",
            "  --forbid_formal_seeds 11 12 13 \\",
            "  --fixed_dp_head \"$REQUIRED_DP_HEAD\" \\",
            "  --candidate_operation \"fixed DP candidate reranking only\" \\",
            "  --score_expression \"score_k(w)=a_k^T w\" \\",
            "  --write_zero_overlap_registries",
            "",
            "# No CAMP trajectory generation, DP modification, training, replay, promotion, or deployment.",
            "",
        ]
    )


def _checks(
    *,
    implementation_static_contract_review_json: Path,
    v13_audit_md: Path,
    source_review: dict[str, Any],
    source_decision: dict[str, Any],
    review_contract: dict[str, Any],
    audit_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    target_min_candidate_members: int,
    target_candidates_per_member: int,
    authorized_current_work: str,
    enabled: bool,
    runbook: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    add = checks.append
    add(_expect("builder_enabled", enabled, True))
    add(_expect("implementation_static_contract_review_json_exists", implementation_static_contract_review_json.exists(), True))
    add(_expect("v13_audit_exists", v13_audit_md.exists(), True))
    add(_expect("source_schema_version", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA_VERSION))
    add(_expect("source_status", source_decision.get("status"), SOURCE_REVIEW_PASS_STATUS))
    add(_expect("source_passed", source_decision.get("passed"), True))
    add(_expect("source_failed_checks_empty", source_decision.get("failed_checks"), []))
    add(_expect("source_authorized_next_work", source_decision.get("authorized_next_work"), authorized_current_work))
    add(_expect("source_authorizes_implementation", source_decision.get("fixed_dp_candidate_generation_implementation_authorized_next"), True))
    add(_expect("source_review_contract_generator_script", review_contract.get("future_generator_script"), "scripts/integrations/build_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation.py"))
    for flag in SOURCE_FALSE_FLAGS:
        add(_expect(f"source_forbids_{flag}", source_decision.get(flag), False))
    add(_expect("source_candidate_operation", source_decision.get("candidate_operation"), "fixed DP candidate reranking only"))
    add(_expect("source_score_expression", source_decision.get("score_expression"), SCORE_EXPRESSION))
    add(_expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main))
    add(_expect("current_dp_head_fixed", current_dp_head, required_dp_head))
    add(_expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD))
    add(_expect("target_members_at_least_1000", target_min_candidate_members >= 1000, True))
    add(_expect("target_candidates_per_member", target_candidates_per_member, TARGET_CANDIDATES_PER_MEMBER))
    add(_expect("audit_latest_status", _latest_value(audit_text, "current_v13_status"), LATEST_AUDIT_STATUS))
    add(_expect("audit_latest_next_work", _latest_value(audit_text, "next_work_target"), authorized_current_work))
    add(_expect("audit_authorizes_implementation", _latest_value(audit_text, "fixed_dp_candidate_generation_implementation_authorized_next"), "True"))
    for flag in AUDIT_FALSE_FLAGS:
        add(_expect(f"audit_forbids_{flag}", _latest_value(audit_text, flag), "False"))
    add(_expect("runbook_guard_env_present", GUARD_ENV_VAR in runbook, True))
    add(_expect("runbook_checks_dp_head", "DP HEAD mismatch" in runbook, True))
    add(_expect("runbook_forbids_formal_seeds", "--forbid_formal_seeds 11 12 13" in runbook, True))
    add(_expect("runbook_writes_zero_overlap_registries", "--write_zero_overlap_registries" in runbook, True))
    for seed in FORMAL_SEEDS:
        add(_expect(f"formal_seed_{seed}_not_authorized", f"seed {seed}" in runbook.lower(), False))
    return checks


def _decision(
    *,
    passed: bool,
    failed: list[str],
    enabled: bool,
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    if not enabled:
        status = DISABLED_STATUS
    else:
        status = READY_STATUS if passed else REJECT_STATUS
    return {
        "status": status,
        "passed": passed,
        "failed_checks": failed,
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "fixed_dp_candidate_generation_implementation_complete": passed,
        "post_implementation_static_contract_review_authorized_next": passed,
        "fixed_dp_candidate_generation_authorized_next": False,
        "fixed_dp_candidate_generation_execution_authorized_next": False,
        "fixed_dp_candidate_generation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "data_preparation_authorized_next": False,
        "replay_execution_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "training_executed": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }


def _write_outputs(
    *,
    output_paths: dict[str, Path],
    runbook: str,
    dp_repo: str,
    camp_repo: str,
    dp_entrypoint: str,
    target_min_candidate_members: int,
    target_candidates_per_member: int,
    required_dp_head: str,
) -> None:
    for path in output_paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "runbook_schema_version": RUNBOOK_SCHEMA_VERSION,
        "fixed_dp_candidate_generation_executed": False,
        "candidate_generation_by_camp": False,
        "trajectory_generation_by_camp": False,
        "trajectory_modification_by_camp": False,
        "dp_modification": False,
        "required_dp_head": required_dp_head,
        "dp_repo": dp_repo,
        "camp_repo": camp_repo,
        "dp_entrypoint": dp_entrypoint,
        "target_min_candidate_members": target_min_candidate_members,
        "target_candidates_per_member": target_candidates_per_member,
        "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
        "forbidden_sources": [
            "CAMP trajectory generation",
            "CAMP trajectory repair",
            "CAMP trajectory rewrite",
            "reference_blend",
            "guidance",
            "postprocess",
            "postselection",
            "closed-loop outcomes",
            "Full36",
            "formal seeds 11/12/13",
        ],
        "runbook": str(output_paths["runbook"]),
    }
    output_paths["manifest"].write_text(
        json.dumps(_stable(manifest), indent=2) + "\n",
        encoding="utf-8",
    )
    output_paths["runbook"].write_text(runbook, encoding="utf-8")
    for key in (
        "candidate_tensor_hash_registry_template",
        "path_signature_registry_template",
        "record_identity_registry_template",
        "split_manifest_root_registry_template",
    ):
        output_paths[key].write_text(
            json.dumps({"schema_version": f"{MANIFEST_SCHEMA_VERSION}.{key}", "values": []}, indent=2)
            + "\n",
            encoding="utf-8",
        )
    output_paths["zero_overlap_preflight_inputs_template"].write_text(
        json.dumps(
            {
                "schema_version": "dp_camp_v13_fixed_dp_candidate_generation_zero_overlap_preflight_inputs_v1",
                "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
                "candidate_tensor_hash_registry": str(output_paths["candidate_tensor_hash_registry_template"]),
                "path_signature_registry": str(output_paths["path_signature_registry_template"]),
                "record_identity_registry": str(output_paths["record_identity_registry_template"]),
                "split_manifest_root_registry": str(output_paths["split_manifest_root_registry_template"]),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _output_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "manifest": output_dir / "fixed_dp_candidate_generation_manifest.json",
        "runbook": output_dir / "run_fixed_dp_candidate_generation.sh",
        "candidate_tensor_hash_registry_template": output_dir / "candidate_tensor_hash_registry_template.json",
        "path_signature_registry_template": output_dir / "path_signature_registry_template.json",
        "record_identity_registry_template": output_dir / "record_identity_registry_template.json",
        "split_manifest_root_registry_template": output_dir / "split_manifest_root_registry_template.json",
        "zero_overlap_preflight_inputs_template": output_dir / "zero_overlap_preflight_inputs_template.json",
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = _dict(report.get("final_decision"))
    builder = _dict(report.get("generation_builder"))
    failed = decision.get("failed_checks") or []
    return "\n".join(
        [
            "# Fixed-DP Candidate Generation Builder",
            "",
            f"- Status: `{decision.get('status')}`",
            f"- Passed: `{decision.get('passed')}`",
            f"- Failed checks: `{failed}`",
            f"- Authorized next work: `{decision.get('authorized_next_work')}`",
            f"- Builder enabled: `{builder.get('builder_enabled')}`",
            f"- Manifest written: `{builder.get('manifest_written')}`",
            f"- Fixed-DP generation executed: `{decision.get('fixed_dp_candidate_generation_executed')}`",
            f"- Fixed-DP generation execution authorized next: `{decision.get('fixed_dp_candidate_generation_execution_authorized_next')}`",
            f"- CAMP candidate generation authorized: `{decision.get('candidate_generation_by_camp_authorized')}`",
            f"- Training preflight authorized next: `{decision.get('training_preflight_authorized_next')}`",
            f"- Training execution authorized next: `{decision.get('training_execution_authorized_next')}`",
            f"- DP modification authorized: `{decision.get('dp_modification_authorized')}`",
            f"- Candidate operation: `{decision.get('candidate_operation')}`",
            f"- Score expression: `{decision.get('score_expression')}`",
            "",
        ]
    )


def _load_json_dict(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object at {path}")
    return payload


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": actual == expected, "actual": actual, "expected": expected}


def _latest_value(text: str, key: str) -> str | None:
    token = f"{key}="
    if token not in text:
        return None
    return text.rsplit(token, maxsplit=1)[1].splitlines()[0].strip()


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
