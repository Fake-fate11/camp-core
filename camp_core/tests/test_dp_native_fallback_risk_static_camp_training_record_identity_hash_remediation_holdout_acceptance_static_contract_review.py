from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "audit_diffusion_planner_dp_native_fallback_risk_static_camp_training_development_holdout_acceptance.py"
)
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_record_identity_hash_remediation_holdout_acceptance_static_contract_review.md"
)
CHAIN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_record_identity_hash_remediation_acceptance_chain.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _tree() -> ast.Module:
    return ast.parse(_source())


def test_record_identity_holdout_static_review_records_scope_and_static_findings() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "default_off_before_reads=True",
        "read_only_existing_artifacts=True",
        "writes_only_explicit_output_json_and_md=True",
        "subprocess_usage=False",
        "dp_execution_path=False",
        "candidate_generation_path=False",
        "camp_retraining_path=False",
        "trajectory_generation_path=False",
        "trajectory_rewrite_path=False",
        "selector_or_atom_promotion_path=False",
        "deployment_path=False",
        "blocking_contract_findings=0",
    ]:
        assert needle in text


def test_holdout_audit_default_off_precedes_artifact_reads() -> None:
    tree = _tree()
    audit_fn = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "audit_development_holdout_acceptance"
    )

    enabled_index = audit_fn.args.kwonlyargs.index(next(arg for arg in audit_fn.args.kwonlyargs if arg.arg == "enabled"))
    assert isinstance(audit_fn.args.kw_defaults[enabled_index], ast.Constant)
    assert audit_fn.args.kw_defaults[enabled_index].value is False

    disabled_return_index = None
    first_hash_read_index = None
    for index, node in enumerate(audit_fn.body):
        if isinstance(node, ast.If) and ast.unparse(node.test) == "not enabled":
            disabled_return_index = index
        if isinstance(node, ast.For) and "_sha256_file_if_present" in ast.unparse(node):
            first_hash_read_index = index
    assert disabled_return_index is not None
    assert first_hash_read_index is not None
    assert disabled_return_index < first_hash_read_index


def test_holdout_audit_writes_only_reports_and_uses_no_process_launches() -> None:
    tree = _tree()
    write_receivers = []
    mkdir_receivers = []
    forbidden_calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            receiver = ast.unparse(node.func.value)
            if node.func.attr == "write_text":
                write_receivers.append(receiver)
            if node.func.attr == "mkdir":
                mkdir_receivers.append(receiver)
            if receiver in {"subprocess", "os"} and node.func.attr in {"system", "popen", "run", "Popen"}:
                forbidden_calls.append(f"{receiver}.{node.func.attr}")

    assert write_receivers == ["args.output_json", "args.output_md"]
    assert mkdir_receivers == ["args.output_json.parent", "args.output_md.parent"]
    assert forbidden_calls == []


def test_record_identity_holdout_static_review_preserves_reranker_contract() -> None:
    source = _source()
    review = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        '"records_scope": "validation_groups_only"',
        '"fallback_branch_only": True',
        '"records_without_feasible_candidate_only": True',
        '"fixed_dp_candidate_reranking_only": True',
        '"score_expression": "score_k(w)=a_k^T w"',
        '"selection_rule": "argmin_k score_k(w)"',
        "APPROVED_ATOM_SCHEMA",
        "APPROVED_ATOM_NAMES",
        "require_weights_simplex_nonnegative=True",
        "require_atom_scales_strictly_positive=True",
        "candidate_tensor_unchanged=True",
        "pre_post_candidate_provenance_hashes_equal_if_present=True",
    ]:
        assert needle in source + review


def test_record_identity_training_chain_remains_nonpromotion_without_claims() -> None:
    review = REVIEW_DOC.read_text(encoding="utf-8")
    chain = CHAIN_DOC.read_text(encoding="utf-8")

    for needle in [
        "training_chain_status=fallback_risk_static_camp_training_record_identity_hash_remediation_acceptance_chain_passed",
        "camp_retraining_completed=True",
        "post_training_nonpromotion_artifact_audit_passed=True",
        "development_holdout_acceptance_audit_passed=True",
        "training_artifacts_nonpromotion=True",
        "deployment_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "dp_modification_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "does not authorize promotion or claim performance improvement",
    ]:
        assert needle in review + chain

    for forbidden in [
        "deployment_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "dp_modification_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in review + chain


def test_iteration_audit_records_record_identity_static_review_next_gate() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-190:])

    for needle in [
        "status=fallback_risk_static_camp_training_record_identity_hash_remediation_holdout_acceptance_static_contract_review_passed",
        "static_contract_review_complete=True",
        "paper_consistent_fixed_candidate_reranker_boundary_preserved=True",
        "record_identity_training_chain_remains_nonpromotion=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fixed_artifact_fallback_risk_ranking_audit_only",
    ]:
        assert needle in audit

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_unit_tests_only`"
    )
