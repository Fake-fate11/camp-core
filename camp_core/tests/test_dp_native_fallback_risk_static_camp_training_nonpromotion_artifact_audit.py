from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.integrations.audit_diffusion_planner_dp_native_fallback_risk_static_camp_training_nonpromotion_artifact import (  # noqa: E402
    COMPLETE_STATUS,
    DISABLED_STATUS,
    REJECT_STATUS,
    audit_fallback_risk_static_camp_training_nonpromotion_artifact,
    main,
)
from scripts.integrations.train_diffusion_planner_dp_native_fallback_risk_static_camp import (  # noqa: E402
    COMPLETE_STATUS as TRAINING_COMPLETE_STATUS,
    TRAINING_SCHEMA_VERSION,
)
from scripts.integrations.validate_dp_native_fallback_risk_training_sufficiency_preflight import (  # noqa: E402
    APPROVED_ATOM_NAMES,
    APPROVED_ATOM_SCHEMA,
)


SCRIPT = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "audit_diffusion_planner_dp_native_fallback_risk_static_camp_training_nonpromotion_artifact.py"
)
RESULT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_post_training_nonpromotion_artifact_audit.md"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
TRAINING_COMMIT = "0e3b7f3397adecdac559027856efcdb918269496"
CURRENT_CAMP_HEAD = "96f306a70d0b9c139dc726fbac8ad7176e14ef8d"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _false_flags() -> dict[str, bool]:
    return {
        "replay_execution_authorized": False,
        "candidate_generation_authorized": False,
        "Full36_authorized": False,
        "formal_seeds_11_12_13_authorized": False,
        "dp_modification_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_postselection_authorized": False,
        "closed_loop_outcome_online_input_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "feasible_ranking_master_change_authorized": False,
        "hard_feasibility_relaxation_authorized": False,
        "all_infeasible_records_added_to_feasible_training": False,
        "production_selector_change_authorized": False,
        "online_selector_change_authorized": False,
    }


def _base_artifacts(tmp_path: Path) -> dict[str, Path | str]:
    weights = np.zeros((len(APPROVED_ATOM_NAMES),), dtype=np.float64)
    weights[0] = 1.0
    scales = [1.0 + float(index) * 0.01 for index in range(len(APPROVED_ATOM_NAMES))]

    weights_npy = tmp_path / "offline_weights_dp_fallback_risk_static.npy"
    weights_json = tmp_path / "offline_weights_dp_fallback_risk_static.json"
    scales_json = tmp_path / "atom_scales_dp_fallback_risk_static.json"
    np.save(weights_npy, weights)
    _write_json(
        weights_json,
        {
            "atom_schema_version": APPROVED_ATOM_SCHEMA,
            "atom_names": list(APPROVED_ATOM_NAMES),
            "weights": weights.tolist(),
            "score_expression": "score_k(w)=a_k^T w",
            "fallback_only": True,
            "selector_promotion_executed": False,
            "source_hashes": {},
        },
    )
    _write_json(
        scales_json,
        {
            "atom_schema_version": APPROVED_ATOM_SCHEMA,
            "atom_names": list(APPROVED_ATOM_NAMES),
            "scales": scales,
            "source_scale_manifest_sha256": "a" * 64,
        },
    )

    summary = {
        "schema_version": TRAINING_SCHEMA_VERSION,
        "analysis": {
            "name": "dp_native_fallback_risk_static_camp_training_v1",
            "default_off": True,
            "enabled": True,
            "reads_fixed_artifacts_only": True,
            "fallback_only": True,
            "replay_executed": False,
            "candidate_generation_executed": False,
            "diffusion_planner_executed": False,
            "diffusion_planner_modified": False,
            "trajectory_generation_executed": False,
            "trajectory_rewrite_executed": False,
            "postprocess_postselection_executed": False,
            "selector_promotion_executed": False,
            "atom_promotion_executed": False,
        },
        "source_hashes": {},
        "training": {
            "training_type": "dp_native_fallback_risk_static_candidate_reranking",
            "training_scope": "fallback_only_all_infeasible_fixed_dp_candidates",
            "score_expression": "score_k(w)=a_k^T w",
            "objective": "simplex_hinge_cvar_l2",
            "risk_type": "cvar",
            "alpha": 0.8,
            "epochs": 400,
            "lr": 0.05,
            "l2_reg": 0.001,
            "training_seed_recorded": 23,
            "training_records": 13,
            "validation_records": 2,
            "num_candidates": 4,
            "num_atoms": len(APPROVED_ATOM_NAMES),
            "atom_schema_version": APPROVED_ATOM_SCHEMA,
            "atom_names": list(APPROVED_ATOM_NAMES),
            "trained_weights": weights.tolist(),
            "weights_sum": 1.0,
            "weights_min": 0.0,
            "weights_max": 1.0,
            "history": [],
            "train_metrics": {"oracle_match_rate": 0.25, "mean_violation": 0.5},
            "validation_metrics": {"oracle_match_rate": 0.5, "mean_violation": 0.1},
        },
        "output_artifacts": {
            "output_dir": str(tmp_path),
            "weights_npy": str(weights_npy),
            "weights_json": str(weights_json),
            "atom_scales_json": str(scales_json),
            "weights_npy_sha256": _sha(weights_npy),
            "weights_json_sha256": _sha(weights_json),
            "atom_scales_json_sha256": _sha(scales_json),
        },
        "final_decision": {
            "status": TRAINING_COMPLETE_STATUS,
            "passed": True,
            "enabled": True,
            "errors": [],
            "training_authorized": True,
            "training_execution_authorized": True,
            "training_executed": True,
            "camp_retraining_authorized_now": True,
            "fallback_risk_training_authorized_now": True,
            "fixed_dp_candidate_reranking_only": True,
            "fallback_only_training": True,
            **_false_flags(),
        },
    }
    summary_json = _write_json(tmp_path / "training_summary.json", summary)

    return {
        "training_summary_json": summary_json,
        "expected_training_summary_sha256": _sha(summary_json),
        "weights_json": weights_json,
        "expected_weights_json_sha256": _sha(weights_json),
        "weights_npy": weights_npy,
        "expected_weights_npy_sha256": _sha(weights_npy),
        "atom_scales_json": scales_json,
        "expected_atom_scales_json_sha256": _sha(scales_json),
        "training_commit": TRAINING_COMMIT,
        "current_camp_head": CURRENT_CAMP_HEAD,
        "required_dp_head": DP_HEAD,
    }


def test_nonpromotion_artifact_audit_is_default_off_and_does_not_read_missing_inputs(tmp_path: Path) -> None:
    report = audit_fallback_risk_static_camp_training_nonpromotion_artifact(
        training_summary_json=tmp_path / "missing_summary.json",
        expected_training_summary_sha256="a" * 64,
        weights_json=tmp_path / "missing_weights.json",
        expected_weights_json_sha256="b" * 64,
        weights_npy=tmp_path / "missing_weights.npy",
        expected_weights_npy_sha256="c" * 64,
        atom_scales_json=tmp_path / "missing_scales.json",
        expected_atom_scales_json_sha256="d" * 64,
        training_commit=TRAINING_COMMIT,
        current_camp_head=CURRENT_CAMP_HEAD,
        required_dp_head=DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["source_hashes"] == {}


def test_nonpromotion_artifact_audit_accepts_clean_fixed_candidate_artifacts(tmp_path: Path) -> None:
    artifacts = _base_artifacts(tmp_path)
    output_json = tmp_path / "out" / "audit.json"
    output_md = tmp_path / "out" / "audit.md"

    exit_code = main(
        [
            "--training_summary_json",
            str(artifacts["training_summary_json"]),
            "--expected_training_summary_sha256",
            str(artifacts["expected_training_summary_sha256"]),
            "--weights_json",
            str(artifacts["weights_json"]),
            "--expected_weights_json_sha256",
            str(artifacts["expected_weights_json_sha256"]),
            "--weights_npy",
            str(artifacts["weights_npy"]),
            "--expected_weights_npy_sha256",
            str(artifacts["expected_weights_npy_sha256"]),
            "--atom_scales_json",
            str(artifacts["atom_scales_json"]),
            "--expected_atom_scales_json_sha256",
            str(artifacts["expected_atom_scales_json_sha256"]),
            "--training_commit",
            str(artifacts["training_commit"]),
            "--current_camp_head",
            str(artifacts["current_camp_head"]),
            "--required_dp_head",
            str(artifacts["required_dp_head"]),
            "--enable_default_off_fallback_risk_static_camp_training_nonpromotion_artifact_audit",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )
    report = json.loads(output_json.read_text(encoding="utf-8"))
    md = output_md.read_text(encoding="utf-8")

    assert exit_code == 0
    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert report["final_decision"]["post_training_nonpromotion_artifact_audit_passed"] is True
    assert report["final_decision"]["training_artifacts_nonpromotion"] is True
    assert report["final_decision"]["training_authorized"] is False
    assert report["final_decision"]["training_execution_authorized"] is False
    assert report["final_decision"]["selector_promotion_authorized"] is False
    assert report["final_decision"]["atom_promotion_authorized"] is False
    assert report["final_decision"]["deployment_authorized"] is False
    assert report["artifact_checks"]["weights_json_simplex_nonnegative"] is True
    assert report["artifact_checks"]["weights_npy_simplex_nonnegative"] is True
    assert report["artifact_checks"]["weights_json_matches_npy"] is True
    assert "score_expression=score_k(w)=a_k^T w" in md
    assert "training_authorized=False" in md


def test_nonpromotion_artifact_audit_rejects_promotion_flags_and_bad_simplex(tmp_path: Path) -> None:
    artifacts = _base_artifacts(tmp_path)
    summary_path = Path(artifacts["training_summary_json"])
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["final_decision"]["selector_promotion_authorized"] = True
    summary["final_decision"]["safety_benefit_claim_authorized"] = True
    summary_path.write_text(json.dumps(summary, sort_keys=True), encoding="utf-8")

    weights_json = Path(artifacts["weights_json"])
    payload = json.loads(weights_json.read_text(encoding="utf-8"))
    payload["weights"][0] = -0.2
    payload["weights"][1] = 1.2
    weights_json.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = audit_fallback_risk_static_camp_training_nonpromotion_artifact(
        **artifacts,
        enabled=True,
    )
    errors = report["final_decision"]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    for needle in [
        "training_summary_json_sha256_mismatch",
        "weights_json_sha256_mismatch",
        "training_final_decision_selector_promotion_authorized_not_false",
        "training_final_decision_safety_benefit_claim_authorized_not_false",
        "weights_json_weights_not_simplex_nonnegative",
        "training_trained_weights_json_mismatch",
    ]:
        assert needle in errors


def test_nonpromotion_artifact_audit_script_is_read_only_and_default_off() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    audit_fn = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "audit_fallback_risk_static_camp_training_nonpromotion_artifact"
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

    write_receivers = []
    subprocess_calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        receiver = ast.unparse(node.func.value)
        if node.func.attr == "write_text":
            write_receivers.append(receiver)
        if receiver == "subprocess":
            subprocess_calls.append(node.func.attr)
    assert write_receivers == ["args.output_json", "args.output_md"]
    assert subprocess_calls == []
    assert "--enable_default_off_fallback_risk_static_camp_training_nonpromotion_artifact_audit" in source


def test_nonpromotion_artifact_audit_docs_pin_the_next_gate_and_no_promotion_claims() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=dp_native_fallback_risk_static_camp_training_nonpromotion_artifact_audit_complete",
        "post_training_nonpromotion_artifact_audit_passed=True",
        "training_artifacts_nonpromotion=True",
        "fixed_dp_candidate_reranking_only=True",
        "score_expression=score_k(w)=a_k^T w",
        "weights_json_simplex_nonnegative=True",
        "weights_npy_simplex_nonnegative=True",
        "weights_json_matches_npy=True",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_development_holdout_acceptance_plan_only",
    ]:
        assert needle in text

    assert "status=fallback_risk_static_camp_training_nonpromotion_artifact_audit_passed" in audit
    for forbidden in [
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "deployment_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in text


def test_current_head_f09dc90_nonpromotion_artifact_audit_is_pinned() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "training_commit=adab72980bfad5fa13172d183feda672d766eba9",
        "audit_execution_camp_head=f09dc902252eed428f7cf72ee5bcefd22f2f235b",
        "training_summary_json_sha256=5b362f29f3737a1015ea977401c5fdafe2cff8e87426555d1ab7140c3ecc8761",
        "offline_weights_json_sha256=75e879d5f9345e49d2ccf4b477ba26863016fe6bcf6adb05c9c48a7cdd772b03",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "atom_scales_json_sha256=69f3618f21687e08793bf766a57747fa121321be9de3e5a71f5a75b5407cfa88",
        "remote_audit_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_nonpromotion_artifact_audit_f09dc90_20260625T201043Z",
        "remote_audit_json_sha256=3cee7ac6dfbba3c60a9d6a6cb1af6f9fd02badc8d1a61cce8ce3385dd05673c5",
        "remote_audit_md_sha256=f7ee7c31174162342b6d2fab45dd4cec951238f23bb6480b6ebb690256c538c7",
        "post_training_nonpromotion_artifact_audit_passed=True",
        "training_artifacts_nonpromotion=True",
        "weights_json_simplex_nonnegative=True",
        "weights_npy_simplex_nonnegative=True",
        "weights_json_matches_npy=True",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
    ]:
        assert needle in text

    assert (
        "status=fallback_risk_static_camp_training_nonpromotion_artifact_audit_current_head_f09dc90_passed"
        in audit
    )


def test_current_record_identity_nonpromotion_artifact_audit_is_pinned() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")

    for needle in [
        "training_commit=5c913aea29d821dbfb8bf47313309e9a7dafd305",
        "audit_execution_camp_head=fc21a130eb346e94b8a8fba8f1515e27e866ad7d",
        "training_summary_json_sha256=a82d2403276e2aaf3e151271426bfca91e113b4e79735a8ead7a359ee8f24fb4",
        "offline_weights_json_sha256=08fe4290defde501f03e99dc752c95432778b9fb973262255e9cf98ec097d0a3",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "atom_scales_json_sha256=10360c02c3deb38a6504781497b4fb5f082e59e63d3aee961f691f4e853a1b21",
        "remote_audit_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_nonpromotion_artifact_audit_5c913ae_fc21a13_20260626T000000Z",
        "remote_audit_json_sha256=2f9f9c163bb14a0b058d33d051d32d0c153a422429260c1ebea6527e5a556bea",
        "remote_audit_md_sha256=eb3efbd544569fc476c4c8da1b071c5c3b210bf3b92101b405ebba66abd365a6",
        "remote_audit_stdout_log_sha256=798df11d416c0c0e5fd4bd00b537391d5cf4d7f3008932dbb286f155e9a9ca38",
        "remote_audit_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "remote_audit_exit=0",
        "post_training_nonpromotion_artifact_audit_passed=True",
        "training_artifacts_nonpromotion=True",
        "weights_json_simplex_nonnegative=True",
        "weights_npy_simplex_nonnegative=True",
        "weights_json_matches_npy=True",
        "training_authorized=False",
        "training_execution_authorized=False",
        "camp_retraining_authorized_now=False",
        "fallback_risk_training_authorized_now=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
    ]:
        assert needle in text


def test_current_ca07b6a_nonpromotion_artifact_audit_is_pinned() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "training_commit=ca07b6acd82ebb1c195d15b95584fc3ce613d758",
        "audit_execution_camp_head=fa5eeaf601c051dde2e30b6647b5f9eabb991952",
        "training_summary_json_sha256=22aec7885c32fc8b514184fd0eb25f1d177be1f41419a62178607f4a26e5ca11",
        "offline_weights_json_sha256=d05f35bb83ed160f98f498a6d7d80483d2da3f396af8a73cbdbaab31db7e5b5e",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "atom_scales_json_sha256=a1dd6249c59290a7b345d377512fa074a1a4c019d45d30a40637bdbfb8b141d5",
        "remote_audit_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_nonpromotion_artifact_audit_ca07b6a_fa5eeaf_20260626T063405Z",
        "remote_audit_json_sha256=c2c746b557f300720fd2e146d38899cb2574501aa1fe4b17d89c721d517e5cf0",
        "remote_audit_md_sha256=f1626790ddd14463ddad58b4684db086ccb3d23b63ee5221c966d0b594f4c393",
        "remote_audit_stdout_log_sha256=798df11d416c0c0e5fd4bd00b537391d5cf4d7f3008932dbb286f155e9a9ca38",
        "remote_audit_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "remote_audit_exit=0",
        "post_training_nonpromotion_artifact_audit_passed=True",
        "training_artifacts_nonpromotion=True",
        "weights_json_simplex_nonnegative=True",
        "weights_npy_simplex_nonnegative=True",
        "weights_json_matches_npy=True",
        "training_authorized=False",
        "training_execution_authorized=False",
        "camp_retraining_authorized_now=False",
        "fallback_risk_training_authorized_now=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
    ]:
        assert needle in text

    assert (
        "status=fallback_risk_static_camp_training_nonpromotion_artifact_audit_current_head_fa5eeaf_passed"
        in audit
    )


def test_current_34bdb4b_nonpromotion_artifact_audit_is_pinned() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "training_commit=34bdb4b3ac115700568f989c74a54706a0250e09",
        "audit_execution_camp_head=ecc4a6ed5a54c04fafb6b9bf396eed3e6f6841e8",
        "training_summary_json_sha256=c37307b62210204bbd2a26730f9b4c2f209deb1c3d921eabb7214bb168f5c5ce",
        "offline_weights_json_sha256=d5be3af9de82f2032145915e0ce2947248850dc3643a9b0a526a625232bce3fb",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "atom_scales_json_sha256=ff6a513c25d5dd4ac10672c54751023b2ca400b3fd202fcb42bc95d4e24ee7c2",
        "remote_audit_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_nonpromotion_artifact_audit_34bdb4b_ecc4a6e_20260626T134640Z",
        "remote_audit_json_sha256=4acb0ae9405b52479eebeeb63a6fb7fca3e0b66a819a82112f1a47e1880a4fb9",
        "remote_audit_md_sha256=fa275e7a1ca3b5b74ae6f84501dadbec63bc0dcf84b17ebcf4ac207eb25d8dc8",
        "remote_audit_stdout_log_sha256=798df11d416c0c0e5fd4bd00b537391d5cf4d7f3008932dbb286f155e9a9ca38",
        "remote_audit_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "remote_audit_exit=0",
        "post_training_nonpromotion_artifact_audit_passed=True",
        "training_artifacts_nonpromotion=True",
        "weights_json_simplex_nonnegative=True",
        "weights_npy_simplex_nonnegative=True",
        "weights_json_matches_npy=True",
        "training_authorized=False",
        "training_execution_authorized=False",
        "camp_retraining_authorized_now=False",
        "fallback_risk_training_authorized_now=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
    ]:
        assert needle in text

    for needle in [
        "status=fallback_risk_static_camp_training_nonpromotion_artifact_audit_current_head_ecc4a6e_passed",
        "remote_audit_json_sha256=4acb0ae9405b52479eebeeb63a6fb7fca3e0b66a819a82112f1a47e1880a4fb9",
        "weights_json_matches_npy=True",
        "deployment_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in audit


def test_current_8471380_nonpromotion_artifact_audit_is_pinned() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "training_commit=6ca391d1b6f09e6f0a557c8824809032dd50311d",
        "audit_execution_camp_head=84713804e1a2b4360ae850d8fbdd5427d810e342",
        "training_summary_json_sha256=b7ea56145b3a4a8d50f8e5e12bc2f23c6c2c963f14d1907aa4be31a18dd7b4e3",
        "offline_weights_json_sha256=c53d59509c8d338ad3993b9d8a079d9420ab48df05548d3be75fd29235fa0634",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "atom_scales_json_sha256=85fe39a375f59117459d3d4104d589c6dacb12c70add01b878142be23d327aa5",
        "remote_audit_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_nonpromotion_artifact_audit_6ca391d_8471380_20260626T192625Z",
        "remote_audit_json_sha256=0d34d9dd9309f69c914b87c5ef84cb49962d7787575ddde065f4171c8a058520",
        "remote_audit_md_sha256=b9f5a5bf91498948f00e1c6d923bf17930ce0034848349d22661b393749f1183",
        "remote_audit_stdout_log_sha256=798df11d416c0c0e5fd4bd00b537391d5cf4d7f3008932dbb286f155e9a9ca38",
        "remote_audit_stderr_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "remote_audit_exit=0",
        "post_training_nonpromotion_artifact_audit_passed=True",
        "training_artifacts_nonpromotion=True",
        "weights_json_simplex_nonnegative=True",
        "weights_npy_simplex_nonnegative=True",
        "weights_json_matches_npy=True",
        "training_authorized=False",
        "training_execution_authorized=False",
        "camp_retraining_authorized_now=False",
        "fallback_risk_training_authorized_now=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployment_authorized=False",
    ]:
        assert needle in text

    for needle in [
        "status=fallback_risk_static_camp_training_nonpromotion_artifact_audit_current_head_8471380_passed",
        "remote_audit_json_sha256=0d34d9dd9309f69c914b87c5ef84cb49962d7787575ddde065f4171c8a058520",
        "weights_json_matches_npy=True",
        "deployment_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in audit
