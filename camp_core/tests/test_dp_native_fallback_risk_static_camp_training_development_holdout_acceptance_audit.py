from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.integrations.audit_diffusion_planner_dp_native_fallback_risk_static_camp_training_development_holdout_acceptance import (  # noqa: E402
    COMPLETE_STATUS,
    DISABLED_STATUS,
    REJECT_STATUS,
    audit_development_holdout_acceptance,
    main,
)
from scripts.integrations.build_diffusion_planner_dp_native_fallback_risk_training_data import (  # noqa: E402
    DATASET_SCHEMA_VERSION,
)
from scripts.integrations.train_diffusion_planner_dp_native_fallback_risk_static_camp import (  # noqa: E402
    TRAINING_SCHEMA_VERSION,
    COMPLETE_STATUS as TRAINING_COMPLETE_STATUS,
)
from scripts.integrations.validate_dp_native_fallback_risk_training_sufficiency_preflight import (  # noqa: E402
    APPROVED_ATOM_NAMES,
    APPROVED_ATOM_SCHEMA,
)


SCRIPT = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "audit_diffusion_planner_dp_native_fallback_risk_static_camp_training_development_holdout_acceptance.py"
)
RESULT_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_development_holdout_acceptance_audit.md"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CAMP_HEAD = "5398c33a1d5082610892f5b09f34754e716ea071"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _group(source_log: str, run_id: str, record_index: int) -> str:
    return f"{source_log}|{run_id}|{record_index}"


def _atoms(oracle_index: int) -> list[list[float]]:
    high = [4.0] + [1.0 for _ in APPROVED_ATOM_NAMES[1:]]
    low = [0.1] + [1.0 for _ in APPROVED_ATOM_NAMES[1:]]
    return [high, low] if oracle_index == 1 else [low, high]


def _record(source_log: str, run_id: str, record_index: int, *, oracle_index: int = 1) -> dict[str, Any]:
    atoms = _atoms(oracle_index)
    return {
        "schema_version": DATASET_SCHEMA_VERSION,
        "source_log": source_log,
        "source_log_sha256": "a" * 64,
        "source_artifact_sha256": "b" * 64,
        "run_id": run_id,
        "record_index": record_index,
        "selection_step": None,
        "candidate_count": 2,
        "selected_index": 0,
        "oracle_index": oracle_index,
        "oracle_policy": ["red", "lane", "quality"],
        "costs": [
            {"red": 1.0, "lane": 0.8, "quality": 2.0},
            {"red": 0.0, "lane": 0.2, "quality": 1.0},
        ],
        "margins": [1.0, 0.0] if oracle_index == 1 else [0.0, 1.0],
        "atom_schema_version": APPROVED_ATOM_SCHEMA,
        "atom_names": list(APPROVED_ATOM_NAMES),
        "atoms": copy.deepcopy(atoms),
        "normalized_atoms": copy.deepcopy(atoms),
        "training_authorized": False,
        "selected_index_used_as_feature": False,
        "candidate_rank_used_as_feature": False,
        "fallback_label_is_not_a_deployed_atom": True,
    }


def _base_artifacts(tmp_path: Path) -> dict[str, Path | str]:
    train_groups = [_group("log_a", "run_0", 0)]
    validation_groups = [_group("log_b", "run_1", 0)]
    records = [
        _record("log_a", "run_0", 0),
        _record("log_b", "run_1", 0),
    ]
    dataset = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "source_hashes": {"log_a": "a" * 64, "log_b": "a" * 64},
        "record_counts": {
            "records_total": 2,
            "records_without_feasible_candidate": 2,
            "records_with_feasible_candidate": 0,
            "records_built": 2,
            "failed_records": 0,
        },
        "records": records,
        "failed_records": [],
        "final_decision": {"passed": True, "enabled": True, "errors": []},
    }
    dataset_path = _write_json(tmp_path / "dataset.json", dataset)
    split = {
        "schema_version": "dp_native_fallback_risk_training_split_manifest_v1",
        "group_key_fields": ["source_log", "run_id", "record_index"],
        "training_groups": train_groups,
        "validation_groups": validation_groups,
        "seeds": [21, 22],
        "formal_eval_artifact_included": False,
        "record_counts": {"training_records": 1, "validation_records": 1},
        "final_decision": {"passed": True, "enabled": True, "errors": []},
    }
    split_path = _write_json(tmp_path / "split.json", split)
    scales = {
        "schema_version": "dp_native_fallback_risk_training_train_only_scale_manifest_v1",
        "fit_groups": train_groups,
        "excluded_validation_groups": validation_groups,
        "fit_seeds": [21, 22],
        "formal_eval_artifact_included": False,
        "atom_schema_version": APPROVED_ATOM_SCHEMA,
        "atom_names": list(APPROVED_ATOM_NAMES),
        "atom_scales": {name: 1.0 for name in APPROVED_ATOM_NAMES},
        "final_decision": {"passed": True, "enabled": True, "errors": []},
    }
    scales_path = _write_json(tmp_path / "scales.json", scales)
    master = {
        "schema_version": "dp_native_fallback_risk_fallback_master_config_v1",
        "fallback_only": True,
        "feasible_branch_records_allowed": False,
        "all_infeasible_records_added_to_feasible_training": False,
        "all_infeasible_records_relabelled_feasible": False,
        "hard_feasibility_relaxation_authorized": False,
        "feasible_ranking_master_change_authorized": False,
        "score_expression": "score_k(w)=a_k^T w",
        "atoms_fixed_nonnegative": True,
        "fallback_label_is_deployed_atom": False,
        "margins_nonnegative": True,
        "simplex_cvar_l2_convex": True,
    }
    master_path = _write_json(tmp_path / "master.json", master)
    preflight = {
        "schema_version": "dp_native_fallback_risk_training_sufficiency_preflight_v1",
        "source_hashes": {
            "split_manifest": _sha(split_path),
            "scale_manifest": _sha(scales_path),
            "fallback_master_config": _sha(master_path),
        },
        "final_decision": {
            "passed": True,
            "enabled": True,
            "errors": [],
            "training_authorized": False,
        },
    }
    preflight_path = _write_json(tmp_path / "preflight.json", preflight)
    weights = np.zeros((len(APPROVED_ATOM_NAMES),), dtype=np.float64)
    weights[0] = 1.0
    weights_npy = tmp_path / "weights.npy"
    np.save(weights_npy, weights)
    weights_json = _write_json(
        tmp_path / "weights.json",
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
    atom_scales_json = _write_json(
        tmp_path / "atom_scales.json",
        {
            "atom_schema_version": APPROVED_ATOM_SCHEMA,
            "atom_names": list(APPROVED_ATOM_NAMES),
            "scales": [1.0 for _ in APPROVED_ATOM_NAMES],
        },
    )
    summary = {
        "schema_version": TRAINING_SCHEMA_VERSION,
        "analysis": {"default_off": True, "reads_fixed_artifacts_only": True},
        "training": {
            "training_type": "dp_native_fallback_risk_static_candidate_reranking",
            "training_scope": "fallback_only_all_infeasible_fixed_dp_candidates",
            "score_expression": "score_k(w)=a_k^T w",
            "objective": "simplex_hinge_cvar_l2",
            "risk_type": "cvar",
            "training_records": len(train_groups),
            "validation_records": len(validation_groups),
            "num_candidates": 2,
            "num_atoms": len(APPROVED_ATOM_NAMES),
            "atom_schema_version": APPROVED_ATOM_SCHEMA,
            "atom_names": list(APPROVED_ATOM_NAMES),
            "trained_weights": weights.tolist(),
            "weights_sum": 1.0,
            "weights_min": 0.0,
            "weights_max": 1.0,
        },
        "output_artifacts": {},
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
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }
    summary_path = _write_json(tmp_path / "training_summary.json", summary)
    return {
        "dataset_json": dataset_path,
        "expected_dataset_sha256": _sha(dataset_path),
        "training_split_manifest_json": split_path,
        "expected_split_manifest_sha256": _sha(split_path),
        "train_only_scale_manifest_json": scales_path,
        "expected_scale_manifest_sha256": _sha(scales_path),
        "fallback_master_config_json": master_path,
        "expected_master_config_sha256": _sha(master_path),
        "preflight_json": preflight_path,
        "expected_preflight_sha256": _sha(preflight_path),
        "training_summary_json": summary_path,
        "expected_training_summary_sha256": _sha(summary_path),
        "weights_json": weights_json,
        "expected_weights_json_sha256": _sha(weights_json),
        "weights_npy": weights_npy,
        "expected_weights_npy_sha256": _sha(weights_npy),
        "atom_scales_json": atom_scales_json,
        "expected_atom_scales_json_sha256": _sha(atom_scales_json),
        "current_camp_head": CAMP_HEAD,
        "required_dp_head": DP_HEAD,
    }


def test_development_holdout_audit_default_off_does_not_read_missing_inputs(tmp_path: Path) -> None:
    report = audit_development_holdout_acceptance(
        dataset_json=tmp_path / "missing_dataset.json",
        expected_dataset_sha256="a" * 64,
        training_split_manifest_json=tmp_path / "missing_split.json",
        expected_split_manifest_sha256="b" * 64,
        train_only_scale_manifest_json=tmp_path / "missing_scales.json",
        expected_scale_manifest_sha256="c" * 64,
        fallback_master_config_json=tmp_path / "missing_master.json",
        expected_master_config_sha256="d" * 64,
        preflight_json=tmp_path / "missing_preflight.json",
        expected_preflight_sha256="e" * 64,
        training_summary_json=tmp_path / "missing_summary.json",
        expected_training_summary_sha256="f" * 64,
        weights_json=tmp_path / "missing_weights.json",
        expected_weights_json_sha256="1" * 64,
        weights_npy=tmp_path / "missing_weights.npy",
        expected_weights_npy_sha256="2" * 64,
        atom_scales_json=tmp_path / "missing_atom_scales.json",
        expected_atom_scales_json_sha256="3" * 64,
        current_camp_head=CAMP_HEAD,
        required_dp_head=DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["source_hashes"] == {}


def test_development_holdout_audit_accepts_clean_fixed_artifacts_and_cli_outputs(tmp_path: Path) -> None:
    artifacts = _base_artifacts(tmp_path)
    output_json = tmp_path / "out" / "audit.json"
    output_md = tmp_path / "out" / "audit.md"

    args = []
    for key, value in artifacts.items():
        cli_name = "--" + key
        args.extend([cli_name, str(value)])
    args.extend(
        [
            "--enable_default_off_fallback_risk_static_camp_training_development_holdout_acceptance_audit",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )

    exit_code = main(args)
    report = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")

    assert exit_code == 0
    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert report["final_decision"]["development_holdout_acceptance_audit_passed"] is True
    assert report["final_decision"]["training_authorized"] is False
    assert report["final_decision"]["selector_promotion_authorized"] is False
    assert report["holdout"]["validation_records"] == 1
    assert report["holdout"]["selected_index_in_range"] is True
    assert report["holdout"]["candidate_count_unchanged"] is True
    assert report["holdout"]["static_oracle_match_rate"] == 1.0
    assert report["holdout"]["static_selected_min_red_match_rate"] == 1.0
    assert "score_expression=score_k(w)=a_k^T w" in markdown


def test_development_holdout_audit_rejects_formal_seed_bad_weights_and_candidate_mutation(tmp_path: Path) -> None:
    artifacts = _base_artifacts(tmp_path)
    split_path = Path(artifacts["training_split_manifest_json"])
    split = json.loads(split_path.read_text(encoding="utf-8"))
    split["seeds"] = [11]
    split_path.write_text(json.dumps(split, sort_keys=True), encoding="utf-8")
    dataset_path = Path(artifacts["dataset_json"])
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    dataset["records"][1]["candidate_count"] = 3
    dataset_path.write_text(json.dumps(dataset, sort_keys=True), encoding="utf-8")
    weights_json_path = Path(artifacts["weights_json"])
    weights_json = json.loads(weights_json_path.read_text(encoding="utf-8"))
    weights_json["weights"][0] = -0.1
    weights_json["weights"][1] = 1.1
    weights_json_path.write_text(json.dumps(weights_json, sort_keys=True), encoding="utf-8")

    report = audit_development_holdout_acceptance(
        **artifacts,
        enabled=True,
    )
    errors = report["final_decision"]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    for needle in [
        "dataset_sha256_mismatch",
        "split_manifest_sha256_mismatch",
        "weights_json_sha256_mismatch",
        "split_formal_seed_leak",
        "weights_json_not_simplex_nonnegative",
        "record_0_atom_shape_mismatch",
        "record_0_candidate_count_mismatch",
    ]:
        assert needle in errors


def test_development_holdout_audit_script_is_default_off_and_read_only() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source)
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
    assert "--enable_default_off_fallback_risk_static_camp_training_development_holdout_acceptance_audit" in source


def test_development_holdout_audit_docs_pin_nonpromotion_next_gate() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=dp_native_fallback_risk_static_camp_training_development_holdout_acceptance_audit_complete",
        "development_holdout_acceptance_audit_passed=True",
        "audit_only=True",
        "records_scope=validation_groups_only",
        "score_expression=score_k(w)=a_k^T w",
        "selection_rule=argmin_k score_k(w)",
        "candidate_count_unchanged=True",
        "selected_index_in_range=True",
        "training_authorized=False",
        "candidate_generation_authorized=False",
        "selector_promotion_authorized=False",
        "deployment_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_static_camp_training_holdout_acceptance_static_contract_review",
    ]:
        assert needle in text

    assert "status=fallback_risk_static_camp_training_development_holdout_acceptance_audit_passed" in audit


def test_current_head_a263ce5_development_holdout_audit_is_pinned() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "current_camp_head=a263ce5e9257031f0468f0240e873cbdc0421baf",
        "training_summary_json_sha256=5b362f29f3737a1015ea977401c5fdafe2cff8e87426555d1ab7140c3ecc8761",
        "offline_weights_json_sha256=75e879d5f9345e49d2ccf4b477ba26863016fe6bcf6adb05c9c48a7cdd772b03",
        "dataset_json_sha256=682d432f742d4ab68a262cf70955981bc1562cf1dbcf2ec094984a12fcd11498",
        "training_split_manifest_json_sha256=e0a4ec0623f5db0b868465249ce9615b06b86f6c91067702af3bee9fd700db1d",
        "train_only_scale_manifest_json_sha256=92059b9c60e66c96db836821cb0060072402089b915e0bbd87240fc24c602567",
        "remote_audit_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_development_holdout_acceptance_audit_a263ce5_20260625T202013Z",
        "remote_audit_json_sha256=d579ad6853e000f9a8a126a938c7a2f487b212d34d84b0b68b67c6ed58be83bb",
        "remote_audit_md_sha256=a6f4639e1c2bdc22840119e4e31615134533fa0497fd023f38b56e31efd22d5e",
        "development_holdout_acceptance_audit_passed=True",
        "static_oracle_match_rate=0.5",
        "uniform_oracle_match_rate=1.0",
        "holdout_static_underperforms_uniform=True",
        "local_target_pytest=18 passed",
        "autodl_target_pytest=18 passed",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "selector_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text

    assert (
        "status=fallback_risk_static_camp_training_development_holdout_acceptance_audit_current_head_a263ce5_passed"
        in audit
    )


def test_current_head_cfeebea_development_holdout_audit_is_pinned() -> None:
    text = RESULT_DOC.read_text(encoding="utf-8")
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "current_camp_head=cfeebeac093a1705178a3aa4f709c485be4d69c9",
        "training_summary_json_sha256=a82d2403276e2aaf3e151271426bfca91e113b4e79735a8ead7a359ee8f24fb4",
        "offline_weights_json_sha256=08fe4290defde501f03e99dc752c95432778b9fb973262255e9cf98ec097d0a3",
        "offline_weights_npy_sha256=4a7d4e363822afdca2aafad2f138e77c51f00e7a14216e431193cdad66828b40",
        "atom_scales_json_sha256=10360c02c3deb38a6504781497b4fb5f082e59e63d3aee961f691f4e853a1b21",
        "dataset_json_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "training_split_manifest_json_sha256=b76004575fb79916eb5bbb61492645d37b32797e16c8f28cc8b97cb16dae21f4",
        "train_only_scale_manifest_json_sha256=8ec568461fb0887143b28899388544091aa613500673a2ffe7b1891316e62759",
        "fallback_master_config_json_sha256=ea9d8ddf4bbf6a4fdebca9685c6cc1b625c3803837114301bb3537982a030364",
        "preflight_json_sha256=8f68f312188ada4661aa6cb7dc91cbb9c5537df147ac5c3f0851ee6a5d00e8c5",
        "remote_audit_output_dir=/root/autodl-tmp/camp_dp_native_fallback_risk_static_camp_training_development_holdout_acceptance_audit_5c913ae_cfeebea_20260626T000000Z",
        "remote_audit_json_sha256=4517a941f11b1268ce61dc19a62989a6d39cd04835ea3309dd00c95c5a25d523",
        "remote_audit_md_sha256=ca4f43407fbc229fb2cc3dedc7bb9b9d10a24422ab0bfd621351ebfd678b2f90",
        "remote_audit_stdout_log_sha256=c4b0275758fb959b3193d310d5e06097fcd6a8be0b732165e2fbe42f7587966b",
        "remote_artifact_audit_exit=0",
        "development_holdout_acceptance_audit_passed=True",
        "audit_only=True",
        "plan_only=False",
        "validation_records=2",
        "static_oracle_match_rate=0.5",
        "uniform_oracle_match_rate=1.0",
        "holdout_static_underperforms_uniform=True",
        "selector_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text

    assert (
        "status=fallback_risk_static_camp_training_development_holdout_acceptance_audit_current_head_cfeebea_passed"
        in audit
    )
