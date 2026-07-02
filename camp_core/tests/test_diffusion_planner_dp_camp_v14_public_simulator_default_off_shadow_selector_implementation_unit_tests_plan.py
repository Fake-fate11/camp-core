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
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests.py"
)
CAMP_HEAD = "ed8674ccf26c7c05d6c5c35bd4358e3ec60a8354"


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_shadow_unit_tests_plan", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _static_contract_review(
    module,
    *,
    implementation_authorized: bool = False,
    score_expression: str | None = None,
) -> dict:
    return {
        "static_contract_review": {
            "status": "review_passed_no_implementation",
            "runtime_effect": "executed output remains DP Top-1 during shadow phase",
            "candidate_operation": "fixed DP candidate reranking only",
            "candidate_count": 8,
            "score_expression": score_expression or module.SCORE_EXPRESSION,
            "selection_rule": "shadow_selected_index = argmin_k score_k(w)",
            "contracts": [
                "default_off_flag_contract",
                "immutable_artifact_hash_contract",
                "fixed_candidate_tensor_contract",
                "affine_benders_atom_score_contract",
                "dp_top1_runtime_output_contract",
                "fail_closed_observability_contract",
                "no_promotion_no_claims_contract",
            ],
        },
        "unit_tests_plan_requirements": [
            "unit tests must prove default-off behavior before reading missing artifacts",
            "unit tests must prove shadow selection does not change executed DP Top-1 trajectory",
            "unit tests must prove K drift, artifact hash mismatch, and nonfinite scores fail closed",
            "unit tests must prove no candidate generation, mutation, blend, guidance, or postselection path is introduced",
            "unit tests must prove score_k(w)=a_k^T w remains affine in simplex weights",
            "unit tests must prove formal seeds 11, 12, and 13 are rejected or absent",
        ],
        "forbidden_paths": [
            "actual implementation code edits",
            "DP code, weight, config, or invocation modification",
        ],
        "final_decision": {
            "status": module.SOURCE_REVIEW_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": module.SOURCE_AUTHORIZED_NEXT_WORK,
            "default_off_shadow_selector_implementation_unit_tests_plan_authorized": True,
            "default_off_shadow_selector_implementation_authorized": implementation_authorized,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "training_authorized": False,
            "training_execution_authorized": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "executed_trajectory_change_authorized": False,
        },
    }


def _integration_source() -> str:
    return """
class CAMPSelector:
    pass

scores = normalized @ weights
selected_index = int(np.argmin(selection_scores))
"""


def _runner_source() -> str:
    return """
def _dp_camp_finite_candidate_contract():
    pass
parser.add_argument("--camp_selector_mode", choices=("top1", "static"))
mode = "top1"
"""


def _benders_source() -> str:
    return """
def test_fixed_candidate_atom_scores_are_affine_in_simplex_weights():
    pass
def test_robust_margin_master_rejects_negative_atom_coefficients():
    pass
"""


def _fixture(
    tmp_path: Path,
    module,
    *,
    wrong_eof: bool = False,
    implementation_authorized: bool = False,
    score_expression: str | None = None,
) -> dict:
    docs = tmp_path / "docs"
    next_work = "wrong_gate" if wrong_eof else module.SOURCE_AUTHORIZED_NEXT_WORK
    v14_audit = _write(
        docs / "diffusion_planner_v14_iteration_audit.md",
        "\n".join(
            [
                "## Current Section",
                f"current_v14_status={module.SOURCE_REVIEW_STATUS}",
                f"next_work_target={next_work}",
                "",
            ]
        ),
    )
    current_status = _write(
        docs / "diffusion_planner_current_status.md",
        "\n".join(
            [
                f"current_v14_status={module.SOURCE_REVIEW_STATUS}",
                f"next_work_target={module.SOURCE_AUTHORIZED_NEXT_WORK}",
                "",
            ]
        ),
    )
    static_review = _write(
        tmp_path / "static_contract_review.json",
        json.dumps(
            _static_contract_review(
                module,
                implementation_authorized=implementation_authorized,
                score_expression=score_expression,
            ),
            indent=2,
        ),
    )
    integration = _write(tmp_path / "diffusion_planner.py", _integration_source())
    runner = _write(tmp_path / "run_diffusion_planner_camp_replay.py", _runner_source())
    benders = _write(tmp_path / "test_benders.py", _benders_source())
    return {
        "static_contract_review_json": static_review,
        "camp_integration_py": integration,
        "replay_runner_py": runner,
        "benders_contract_test_py": benders,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "plan",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def test_v14_unit_tests_plan_ready_but_does_not_write_tests(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)
    decision = report["final_decision"]

    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["default_off_shadow_selector_implementation_unit_tests_plan_ready"] is True
    assert decision["default_off_shadow_selector_implementation_unit_tests_only_authorized"] is True
    assert decision["default_off_shadow_selector_implementation_authorized"] is False
    assert decision["online_selector_change_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert report["unit_tests_plan"]["status"] == "plan_ready_no_unit_test_code"
    assert (
        kwargs["output_dir"] / "default_off_shadow_selector_implementation_unit_tests_plan.json"
    ).is_file()
    assert (
        kwargs["output_dir"] / "default_off_shadow_selector_implementation_unit_tests_plan.md"
    ).is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_v14_unit_tests_plan_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    kwargs["enabled"] = False

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "plan_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_unit_tests_plan_authorization_missing"
    )


def test_v14_unit_tests_plan_rejects_source_implementation_leak(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, implementation_authorized=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "source_implementation_not_authorized" in report["final_decision"]["failed_checks"]


def test_v14_unit_tests_plan_rejects_score_contract_drift(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, score_expression="score_k(w)=nonlinear(w)")

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "source_review_score_expression" in report["final_decision"]["failed_checks"]


def test_v14_unit_tests_plan_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, wrong_eof=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_v14_unit_tests_plan_markdown_preserves_boundary(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_report(**_fixture(tmp_path, module))

    markdown = module.render_markdown(report)

    assert "Implementation Unit Tests Plan" in markdown
    assert "Unit tests only authorized next: `True`" in markdown
    assert "Implementation authorized: `False`" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "This gate is plan-only" in markdown


def test_v14_unit_tests_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    output_dir = tmp_path / "cli_plan"
    argv = [
        "v14-unit-tests-plan",
        "--static_contract_review_json",
        str(kwargs["static_contract_review_json"]),
        "--camp_integration_py",
        str(kwargs["camp_integration_py"]),
        "--replay_runner_py",
        str(kwargs["replay_runner_py"]),
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
        "--enable_v14_default_off_shadow_selector_implementation_unit_tests_plan",
    ]
    monkeypatch.setattr("sys.argv", argv)

    assert module.main() == 0

    payload = json.loads(
        (output_dir / "default_off_shadow_selector_implementation_unit_tests_plan.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["final_decision"]["status"] == module.READY_STATUS
    assert "Unit Tests Plan" in (
        output_dir / "default_off_shadow_selector_implementation_unit_tests_plan.md"
    ).read_text(encoding="utf-8")
