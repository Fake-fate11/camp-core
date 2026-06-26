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
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_holdout_acceptance_static_contract_review.md"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _source() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _tree() -> ast.Module:
    return ast.parse(_source())


def test_holdout_acceptance_review_records_static_contract() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "default_off_before_reads=True",
        "read_only_existing_artifacts=True",
        "writes_only_explicit_output_json_and_md=True",
        "subprocess_usage=False",
        "dp_execution_path=False",
        "candidate_generation_path=False",
        "camp_retraining_path=False",
        "blocking_contract_findings=0",
    ]:
        assert needle in text


def test_holdout_acceptance_audit_default_off_precedes_artifact_reads() -> None:
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


def test_holdout_acceptance_audit_writes_only_reports_and_uses_no_subprocess() -> None:
    tree = _tree()
    write_receivers = []
    mkdir_receivers = []
    subprocess_calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        receiver = ast.unparse(node.func.value)
        if node.func.attr == "write_text":
            write_receivers.append(receiver)
        if node.func.attr == "mkdir":
            mkdir_receivers.append(receiver)
        if receiver == "subprocess":
            subprocess_calls.append(node.func.attr)

    assert write_receivers == ["args.output_json", "args.output_md"]
    assert mkdir_receivers == ["args.output_json.parent", "args.output_md.parent"]
    assert subprocess_calls == []


def test_holdout_acceptance_audit_preserves_benders_reranker_boundary() -> None:
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
    ]:
        assert needle in source + review


def test_holdout_acceptance_review_forbids_promotion_and_claims() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "training_authorized=False",
        "camp_retraining_authorized_now=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "deployment_authorized=False",
    ]:
        assert needle in text

    for forbidden in [
        "training_authorized=True",
        "camp_retraining_authorized_now=True",
        "replay_execution_authorized=True",
        "candidate_generation_authorized=True",
        "dp_modification_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "deployable_checkpoint_claim_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
        "deployment_authorized=True",
    ]:
        assert forbidden not in text


def test_iteration_audit_records_holdout_static_contract_review_next_gate() -> None:
    text = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_static_camp_training_holdout_acceptance_static_contract_review_passed",
        "static_contract_review_complete=True",
        "paper_consistent_fixed_candidate_reranker_boundary_preserved=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fixed_artifact_fallback_risk_ranking_audit_only",
    ]:
        assert needle in text


def test_current_head_cb9c630_holdout_static_contract_review_is_pinned() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "review_start_head=cb9c630c183323d1654ebe3a7f39ae5a5361b07f",
        "reviewed_holdout_audit_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_development_holdout_acceptance_audit_a263ce5_20260625T202013Z",
        "reviewed_holdout_audit_json_sha256=d579ad6853e000f9a8a126a938c7a2f487b212d34d84b0b68b67c6ed58be83bb",
        "default_off_before_reads=True",
        "read_only_existing_artifacts=True",
        "writes_only_explicit_output_json_and_md=True",
        "subprocess_usage=False",
        "dp_execution_path=False",
        "candidate_generation_path=False",
        "paper_consistent_fixed_candidate_reranker_boundary_preserved=True",
        "score_expression=score_k(w)=a_k^T w",
        "holdout_static_underperforms_uniform=True",
        "blocking_contract_findings=0",
        "local_target_pytest=13 passed",
        "autodl_target_pytest=13 passed",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "selector_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text

    assert (
        "status=fallback_risk_static_camp_training_holdout_acceptance_static_contract_review_current_head_cb9c630_passed"
        in audit
    )


def test_current_head_525e887_holdout_static_contract_review_is_pinned() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "review_start_head=525e887f0c414676a0e20330e6adb3a069234117",
        "reviewed_holdout_audit_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_development_holdout_acceptance_audit_5c913ae_cfeebea_20260626T000000Z",
        "reviewed_holdout_audit_json_sha256=4517a941f11b1268ce61dc19a62989a6d39cd04835ea3309dd00c95c5a25d523",
        "default_off_before_reads=True",
        "read_only_existing_artifacts=True",
        "writes_only_explicit_output_json_and_md=True",
        "subprocess_usage=False",
        "dp_execution_path=False",
        "candidate_generation_path=False",
        "paper_consistent_fixed_candidate_reranker_boundary_preserved=True",
        "score_expression=score_k(w)=a_k^T w",
        "static_oracle_match_rate=0.5",
        "uniform_oracle_match_rate=1.0",
        "holdout_static_underperforms_uniform=True",
        "blocking_contract_findings=0",
        "selector_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text

    assert (
        "status=fallback_risk_static_camp_training_holdout_acceptance_static_contract_review_current_head_525e887_passed"
        in audit
    )
