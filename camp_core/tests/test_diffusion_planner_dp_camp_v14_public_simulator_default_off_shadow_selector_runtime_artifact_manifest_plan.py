from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest.py"
)
CAMP_HEAD = "58f588a53e6abb6eede97ef356538a3a36afe4e6"


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_runtime_manifest_plan", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _weights(module) -> np.ndarray:
    return np.asarray(
        [1.0 / module.EXPECTED_ATOM_COUNT for _ in range(module.EXPECTED_ATOM_COUNT)],
        dtype=np.float64,
    )


def _training_summary(module, weights: np.ndarray) -> dict:
    return {
        "training_type": module.TRAINING_TYPE,
        "label_source": module.TRAINING_LABEL_SOURCE,
        "reward_key": module.TRAINING_REWARD_KEY,
        "reward_progress_weight": 2.0,
        "num_records": 2914,
        "dropped_records_without_feasible_candidate": 286,
        "num_candidates": module.EXPECTED_CANDIDATE_COUNT,
        "num_atoms": module.EXPECTED_ATOM_COUNT,
        "atom_schema_version": module.ATOM_SCHEMA_VERSION,
        "atom_names": list(module.APPROVED_ATOM_NAMES),
        "trained_weights": weights.tolist(),
        "oracle_match_rate": 0.22,
        "feasible_candidate_rate": 0.97,
        "history": [{"epoch": 1.0, "loss": 2.0}],
        "dp_native_training_data_contract": {
            "schema_version": "clean_dp_native_training_data_contract_validator_v1",
            "records": module.EXPECTED_CONTRACT_RECORDS,
            "failed_records": [],
            "passed": True,
            "read_only": True,
            "replay_executed": False,
            "candidate_generation_executed": False,
            "training_execution_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "future_training_input_contract_satisfied": True,
        },
    }


def _atom_scales(module) -> dict:
    return {
        "atom_schema_version": module.ATOM_SCHEMA_VERSION,
        "atom_names": list(module.APPROVED_ATOM_NAMES),
        "scales": [1.0 for _ in module.APPROVED_ATOM_NAMES],
    }


def _implementation_result(module) -> dict:
    return {
        "status": "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_executed",
        "passed": True,
        "failure_class": "None",
        "exit": 0,
        "camp_head": CAMP_HEAD,
        "camp_origin_main": CAMP_HEAD,
        "dp_head": module.FIXED_DP_HEAD,
        "authorized_work": module.IMPLEMENTATION_AUTHORIZED_WORK,
        "training_executed": False,
        "replay_executed": False,
        "candidate_generation_executed": False,
        "dp_modified": False,
        "promotion_executed": False,
        "deployment_executed": False,
        "safety_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def _post_static_review(module, *, plan_authorized: bool = True) -> dict:
    authorized_next = module.SOURCE_AUTHORIZED_NEXT_WORK if plan_authorized else "wrong_gate"
    return {
        "schema_version": module.POST_REVIEW_SCHEMA_VERSION,
        "analysis": {
            "static_only": True,
            "runtime_execution": False,
        },
        "blocked_actions": {
            "training_authorized": False,
            "training_execution_authorized": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "executed_trajectory_change_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
        "static_contract_review": {
            "runtime_schema_version": module.RUNTIME_SCHEMA_VERSION,
            "source_scope": module.SOURCE_SCOPE,
            "executed_output_policy": "dp_top1",
            "candidate_count": module.EXPECTED_CANDIDATE_COUNT,
        },
        "final_decision": {
            "passed": True,
            "status": module.SOURCE_STATUS,
            "failed_checks": [],
            "authorized_next_work": authorized_next,
            "runtime_artifact_manifest_plan_authorized": plan_authorized,
            "runtime_artifact_manifest_materialization_authorized": False,
            "default_off_shadow_selector_runtime_execution_authorized": False,
            "replay_execution_authorized": False,
            "training_execution_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "selector_promotion_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "score_expression": module.SCORE_EXPRESSION,
        },
    }


def _runner_source(module, *, stale_schema: bool = False) -> str:
    schema = (
        "dp_camp_v13_default_off_shadow_selector_runtime_v1"
        if stale_schema
        else module.RUNTIME_SCHEMA_VERSION
    )
    return f'''
DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION = "{schema}"
DEFAULT_OFF_SHADOW_SELECTOR_SOURCE_SCOPE = "{module.SOURCE_SCOPE}"
DEFAULT_OFF_SHADOW_SELECTOR_EXPECTED_K = 8

def _shadow_artifact_entry(): pass
def _mark_shadow_selector_fail_closed(contract, reason): pass
selected_index = 0 if default_off_shadow_selector else baseline_selected_index
record = {{
    "executed_output_policy": "dp_top1",
    "selection_effect": False,
    "online_selector_change": False,
    "score_expression": "{module.SCORE_EXPRESSION}",
}}
'''


def _docs(module, *, complete: bool = False, wrong_next: bool = False) -> tuple[str, str]:
    if complete:
        status = module.READY_STATUS
        next_work = module.AUTHORIZED_NEXT_WORK
    else:
        status = module.SOURCE_STATUS
        next_work = "wrong_gate" if wrong_next else module.SOURCE_AUTHORIZED_NEXT_WORK
    block = "\n".join(
        [
            "## Current V14 Runtime Artifact Manifest Plan Boundary",
            f"current_v14_status={status}",
            f"next_work_target={next_work}",
            "runtime_artifact_manifest_materialization_authorized=False",
            "default_off_shadow_selector_runtime_execution_authorized=False",
            "replay_execution_authorized=False",
            "training_execution_authorized=False",
            "candidate_generation_authorized=False",
            "dp_modification_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    return block, block


def _fixture(
    tmp_path: Path,
    module,
    *,
    weights: np.ndarray | None = None,
    plan_authorized: bool = True,
    stale_schema: bool = False,
    wrong_next: bool = False,
    complete: bool = False,
) -> dict:
    if weights is None:
        weights = _weights(module)
    weights_path = tmp_path / "offline_weights_dp_static.npy"
    np.save(weights_path, weights)
    audit, status = _docs(module, wrong_next=wrong_next, complete=complete)
    return {
        "training_summary_json": _write_json(
            tmp_path / "training_summary.json",
            _training_summary(module, weights),
        ),
        "atom_scales_json": _write_json(tmp_path / "atom_scales_dp_static.json", _atom_scales(module)),
        "static_weights_npy": weights_path,
        "post_static_review_json": _write_json(
            tmp_path / "post_review.json",
            _post_static_review(module, plan_authorized=plan_authorized),
        ),
        "implementation_result_json": _write_json(
            tmp_path / "implementation_result.json",
            _implementation_result(module),
        ),
        "replay_runner_py": _write(tmp_path / "runner.py", _runner_source(module, stale_schema=stale_schema)),
        "v14_audit_md": _write(tmp_path / "audit.md", audit),
        "current_status_md": _write(tmp_path / "status.md", status),
        "output_dir": tmp_path / "plan",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def test_runtime_artifact_manifest_plan_ready_without_materializing(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)
    decision = report["final_decision"]
    plan = report["runtime_artifact_manifest_plan"]

    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["runtime_artifact_manifest_plan_ready"] is True
    assert decision["runtime_artifact_manifest_static_contract_review_authorized"] is True
    assert decision["runtime_artifact_manifest_materialization_authorized"] is False
    assert decision["default_off_shadow_selector_runtime_execution_authorized"] is False
    assert decision["training_executed_by_this_gate"] is False
    assert plan["materialized_by_this_gate"] is False
    assert plan["real_runtime_manifest_materialized"] is False
    assert Path(plan["planned_runtime_manifest_path"]).exists() is False
    assert plan["required_runtime_entries"]["atom_scales"]["logical_name"] == "atom_scales"
    assert plan["required_runtime_entries"]["static_weights"]["logical_name"] == "static_weights"
    assert "--camp_shadow_artifact_manifest <future_runtime_manifest_json>" in plan["planned_runner_args"]
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_runtime_artifact_manifest_plan_is_disabled_until_enabled(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    kwargs["enabled"] = False

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.DISABLED_STATUS
    assert report["plan_checks"] == []


def test_runtime_artifact_manifest_plan_rejects_weight_simplex_drift(tmp_path: Path) -> None:
    module = _load_module()
    weights = _weights(module)
    weights[0] = -0.2

    report = module.build_report(**_fixture(tmp_path, module, weights=weights))

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "static_weights_npy_simplex" in report["final_decision"]["failed_checks"]
    assert "training_weights_simplex" in report["final_decision"]["failed_checks"]


def test_runtime_artifact_manifest_plan_rejects_post_review_without_authorization(tmp_path: Path) -> None:
    module = _load_module()

    report = module.build_report(**_fixture(tmp_path, module, plan_authorized=False))

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "post_review_authorized_next_work" in report["final_decision"]["failed_checks"]
    assert "post_review_runtime_manifest_plan_authorized" in report["final_decision"]["failed_checks"]


def test_runtime_artifact_manifest_plan_rejects_stale_v13_runtime_schema(tmp_path: Path) -> None:
    module = _load_module()

    report = module.build_report(**_fixture(tmp_path, module, stale_schema=True))

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "runner_v14_runtime_schema" in report["final_decision"]["failed_checks"]
    assert "runner_v13_runtime_schema_absent" in report["final_decision"]["failed_checks"]


def test_runtime_artifact_manifest_plan_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()

    report = module.build_report(**_fixture(tmp_path, module, wrong_next=True))

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "audit_latest_boundary_matches_manifest_plan_gate" in report["final_decision"][
        "failed_checks"
    ]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_runtime_artifact_manifest_plan_accepts_completed_boundary(tmp_path: Path) -> None:
    module = _load_module()

    report = module.build_report(**_fixture(tmp_path, module, complete=True))

    assert report["final_decision"]["status"] == module.READY_STATUS
    assert report["final_decision"]["failed_checks"] == []


def test_runtime_artifact_manifest_plan_cli_writes_plan_not_runtime_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    output_dir = tmp_path / "cli_plan"
    argv = [
        "v14-runtime-manifest-plan",
        "--training_summary_json",
        str(kwargs["training_summary_json"]),
        "--atom_scales_json",
        str(kwargs["atom_scales_json"]),
        "--static_weights_npy",
        str(kwargs["static_weights_npy"]),
        "--post_static_review_json",
        str(kwargs["post_static_review_json"]),
        "--implementation_result_json",
        str(kwargs["implementation_result_json"]),
        "--replay_runner_py",
        str(kwargs["replay_runner_py"]),
        "--v14_audit_md",
        str(kwargs["v14_audit_md"]),
        "--current_status_md",
        str(kwargs["current_status_md"]),
        "--output_dir",
        str(output_dir),
        "--current_camp_head",
        CAMP_HEAD,
        "--current_camp_origin_main",
        CAMP_HEAD,
        "--current_dp_head",
        module.FIXED_DP_HEAD,
        "--enable_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan",
    ]
    monkeypatch.setattr("sys.argv", argv)

    assert module.main() == 0

    payload = json.loads(
        (
            output_dir / "default_off_shadow_selector_runtime_artifact_manifest_plan.json"
        ).read_text(encoding="utf-8")
    )
    plan = payload["runtime_artifact_manifest_plan"]
    assert payload["schema_version"] == module.SCHEMA_VERSION
    assert plan["runtime_schema_version"] == module.RUNTIME_SCHEMA_VERSION
    assert plan["materialized_by_this_gate"] is False
    assert Path(plan["planned_runtime_manifest_path"]).exists() is False
    assert "plan-only" in (
        output_dir / "default_off_shadow_selector_runtime_artifact_manifest_plan.md"
    ).read_text(encoding="utf-8")
