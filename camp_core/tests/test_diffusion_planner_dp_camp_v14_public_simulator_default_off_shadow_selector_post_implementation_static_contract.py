import importlib.util
import json
import sys
from pathlib import Path


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
    / "review_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_post_implementation_static_contract.py"
)
CAMP_HEAD = "56b00fe1c81472535deb6b1311eaf0b6d463ae7a"


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_shadow_post_static_review", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _implementation_result(module, *, passed: bool = True) -> dict:
    return {
        "status": "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_executed",
        "passed": passed,
        "failure_class": "None" if passed else "unit_failure",
        "exit": 0 if passed else 1,
        "camp_head": CAMP_HEAD,
        "camp_origin_main": CAMP_HEAD,
        "dp_head": module.FIXED_DP_HEAD,
        "authorized_work": (
            "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
            "shadow_replay_evaluation_default_off_shadow_selector_"
            "implementation_only_after_explicit_user_authorization"
        ),
        "training_executed": False,
        "replay_executed": False,
        "candidate_generation_executed": False,
        "dp_modified": False,
        "promotion_executed": False,
        "deployment_executed": False,
        "safety_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def _runner_source(
    module,
    *,
    stale_schema: bool = False,
    missing_top1_override: bool = False,
) -> str:
    schema = (
        "dp_camp_v13_default_off_shadow_selector_runtime_v1"
        if stale_schema
        else module.RUNTIME_SCHEMA_VERSION
    )
    top1_override = (
        "selected_index = baseline_selected_index"
        if missing_top1_override
        else "selected_index = 0 if default_off_shadow_selector else baseline_selected_index"
    )
    return f'''
DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION = "{schema}"
DEFAULT_OFF_SHADOW_SELECTOR_SOURCE_SCOPE = "{module.SOURCE_SCOPE}"
DEFAULT_OFF_SHADOW_SELECTOR_EXPECTED_K = 8
parser.add_argument("--camp_default_off_shadow_selector", action="store_true")

def _default_off_shadow_selector_contract(args): pass
def _summarize_default_off_shadow_selector_records(records): pass
def _shadow_artifact_entry(): pass
def _mark_shadow_selector_fail_closed(contract, reason): pass

failed_checks = ["candidate_count_drift", "selector_artifact_load_failed"]
shadow_selected_index = (
            baseline_selected_index if default_off_shadow_selector else None
)
{top1_override}
selected_trajectory = candidates[selected_index]
record = {{
    "executed_output_policy": "dp_top1",
    "selection_effect": False,
    "online_selector_change": False,
    "score_expression": "score_k(w)=a_k^T w",
}}
raise ValueError("--camp_default_off_shadow_selector cannot be combined with --camp_underprogress_relaxation; shadow execution must remain DP Top-1")
flags = [
    "--camp_perfect_tracker_command_postselection",
    "--camp_underprogress_relaxation",
    "--camp_splice_shadow_rule",
]
validation["camp_default_off_shadow_selector"] = camp_default_off_shadow_selector
'''


def _unit_test_source(module) -> str:
    return f'''
from scripts.integrations.run_diffusion_planner_camp_replay import (
    DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION,
    DEFAULT_OFF_SHADOW_SELECTOR_SOURCE_SCOPE,
)

def test_default_off_disabled_contract_returns_dp_top1_before_artifact_reads(): pass
def test_immutable_artifact_hash_contract_fails_closed_on_mismatch(): pass
def test_fixed_candidate_affine_score_contract_uses_real_selector_matrix_product(): pass
def test_k_drift_and_selector_mode_drift_fail_closed(): pass
def test_dp_top1_shadow_runtime_contract_logs_shadow_without_routing(): pass
def test_no_candidate_mutation_contract_keeps_tensor_hash_and_returns_copy(): pass
def test_benders_boundary_keeps_scores_affine_in_simplex_weights(): pass
def test_formal_seed_boundary_is_rejection_only_and_never_replay_execution(): pass
def test_runner_shadow_selector_rejects_execution_changing_flags(): pass
def test_current_static_source_surfaces_preserve_rerank_boundary(): pass

assert DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION == "{module.RUNTIME_SCHEMA_VERSION}"
assert "v13" not in DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION
assert DEFAULT_OFF_SHADOW_SELECTOR_SOURCE_SCOPE == "{module.SOURCE_SCOPE}"
'''


def _benders_source() -> str:
    return """
def test_fixed_candidate_atom_scores_are_affine_in_simplex_weights():
    pass
def test_robust_margin_master_rejects_negative_atom_coefficients():
    pass
"""


def _docs_source(module, *, wrong_eof: bool = False) -> tuple[str, str]:
    next_work = "wrong_gate" if wrong_eof else module.SOURCE_AUTHORIZED_NEXT_WORK
    audit = "\n".join(
        [
            "## Current V14 Default-Off Shadow Selector Implementation Passed",
            f"current_v14_status={module.SOURCE_STATUS}",
            f"next_work_target={next_work}",
            "default_off_shadow_selector_implementation_passed=True",
            "post_implementation_static_contract_review_authorized=True",
            "v14_public_simulator_default_off_shadow_selector_implementation_training_authorized=False",
            "v14_public_simulator_default_off_shadow_selector_implementation_replay_execution_authorized=False",
            "v14_public_simulator_default_off_shadow_selector_implementation_candidate_generation_authorized=False",
            "v14_public_simulator_default_off_shadow_selector_implementation_dp_modification_authorized=False",
            "v14_public_simulator_default_off_shadow_selector_implementation_safety_benefit_claim_authorized=False",
            "v14_public_simulator_default_off_shadow_selector_implementation_camp_over_dp_top1_claim_authorized=False",
            f"v14_public_simulator_default_off_shadow_selector_implementation_score_expression={module.SCORE_EXPRESSION}",
            f"v14_public_simulator_default_off_shadow_selector_implementation_runtime_schema={module.RUNTIME_SCHEMA_VERSION}",
            f"v14_public_simulator_default_off_shadow_selector_implementation_source_scope={module.SOURCE_SCOPE}",
            "",
        ]
    )
    status = "\n".join(
        [
            f"current_v14_status={module.SOURCE_STATUS}",
            f"next_work_target={module.SOURCE_AUTHORIZED_NEXT_WORK}",
            "",
        ]
    )
    return audit, status


def _fixture(
    tmp_path: Path,
    module,
    *,
    wrong_eof: bool = False,
    result_passed: bool = True,
    stale_schema: bool = False,
    missing_top1_override: bool = False,
) -> dict:
    audit, status = _docs_source(module, wrong_eof=wrong_eof)
    return {
        "implementation_result_json": _write(
            tmp_path / "result.json",
            json.dumps(_implementation_result(module, passed=result_passed), indent=2),
        ),
        "replay_runner_py": _write(
            tmp_path / "runner.py",
            _runner_source(
                module,
                stale_schema=stale_schema,
                missing_top1_override=missing_top1_override,
            ),
        ),
        "shadow_unit_test_py": _write(tmp_path / "test_shadow.py", _unit_test_source(module)),
        "benders_contract_test_py": _write(tmp_path / "test_benders.py", _benders_source()),
        "v14_audit_md": _write(tmp_path / "audit.md", audit),
        "current_status_md": _write(tmp_path / "status.md", status),
        "output_dir": tmp_path / "review",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def test_v14_post_implementation_static_review_passes_without_runtime(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)
    decision = report["final_decision"]

    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert (
        decision["default_off_shadow_selector_post_implementation_static_contract_review_passed"]
        is True
    )
    assert decision["runtime_artifact_manifest_plan_authorized"] is True
    assert decision["runtime_artifact_manifest_materialization_authorized"] is False
    assert decision["default_off_shadow_selector_runtime_execution_authorized"] is False
    assert decision["replay_execution_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert report["static_contract_review"]["runtime_schema_version"] == (
        module.RUNTIME_SCHEMA_VERSION
    )
    assert (
        kwargs["output_dir"]
        / "default_off_shadow_selector_post_implementation_static_contract_review.json"
    ).is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_v14_post_implementation_static_review_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    kwargs["enabled"] = False

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "review_enabled" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == (
        "explicit_post_implementation_static_review_authorization_missing"
    )


def test_v14_post_implementation_static_review_rejects_failed_artifact(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_report(**_fixture(tmp_path, module, result_passed=False))

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "implementation_result_passed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == (
        "implementation_artifact_contract_failure"
    )


def test_v14_post_implementation_static_review_rejects_stale_schema(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_report(**_fixture(tmp_path, module, stale_schema=True))

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "runner_v14_runtime_schema" in report["final_decision"]["failed_checks"]
    assert "runner_rejects_v13_runtime_schema" in report["final_decision"]["failed_checks"]


def test_v14_post_implementation_static_review_rejects_shadow_routing(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_report(**_fixture(tmp_path, module, missing_top1_override=True))

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "runner_executed_index_forced_dp_top1" in report["final_decision"][
        "failed_checks"
    ]


def test_v14_post_implementation_static_review_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_report(**_fixture(tmp_path, module, wrong_eof=True))

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_current_repo_v14_post_implementation_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    audit, status = _docs_source(module)
    result_json = _write(
        tmp_path / "result.json",
        json.dumps(_implementation_result(module), indent=2),
    )

    report = module.build_report(
        implementation_result_json=result_json,
        replay_runner_py=ROOT
        / "scripts"
        / "integrations"
        / "run_diffusion_planner_camp_replay.py",
        shadow_unit_test_py=ROOT
        / "camp_core"
        / "tests"
        / "test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests.py",
        benders_contract_test_py=ROOT
        / "camp_core"
        / "tests"
        / "test_diffusion_planner_benders_atom_contract.py",
        v14_audit_md=_write(tmp_path / "audit.md", audit),
        current_status_md=_write(tmp_path / "status.md", status),
        output_dir=tmp_path / "review",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=module.FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == module.READY_STATUS
    assert report["final_decision"]["failed_checks"] == []


def test_v14_post_implementation_static_review_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    output_dir = tmp_path / "cli_review"
    argv = [
        "v14-post-static-review",
        "--implementation_result_json",
        str(kwargs["implementation_result_json"]),
        "--replay_runner_py",
        str(kwargs["replay_runner_py"]),
        "--shadow_unit_test_py",
        str(kwargs["shadow_unit_test_py"]),
        "--benders_contract_test_py",
        str(kwargs["benders_contract_test_py"]),
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
        "--enable_v14_default_off_shadow_selector_post_implementation_static_contract_review",
    ]
    monkeypatch.setattr("sys.argv", argv)

    assert module.main() == 0

    payload = json.loads(
        (
            output_dir
            / "default_off_shadow_selector_post_implementation_static_contract_review.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["final_decision"]["status"] == module.READY_STATUS
    assert "Post-Implementation Static Contract Review" in (
        output_dir
        / "default_off_shadow_selector_post_implementation_static_contract_review.md"
    ).read_text(encoding="utf-8")
