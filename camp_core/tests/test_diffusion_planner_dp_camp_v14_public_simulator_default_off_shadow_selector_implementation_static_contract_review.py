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
    / "review_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_implementation_static_contract.py"
)
CAMP_HEAD = "2a13de6f0d719cdd46ad4e834c34fe8ac1e7b7c7"


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_shadow_implementation_static_review", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _implementation_plan(
    module,
    *,
    implementation_authorized: bool = False,
    score_expression: str | None = None,
) -> dict:
    return {
        "implementation_plan": {
            "status": "plan_ready_no_implementation",
            "selector_phase": "future_default_off_shadow_only",
            "runtime_effect": "log shadow_selected_index while executed output remains DP Top-1",
            "candidate_source": "fixed current-tick DP candidate tensor before CAMP scoring",
            "candidate_count": 8,
            "score_expression": score_expression or module.SCORE_EXPRESSION,
            "selection_rule": "shadow_selected_index = argmin_k score_k(w)",
            "required_steps": [
                "add a default-off shadow selector flag or config whose default is false",
                "load immutable v14 weights, atom scales, and artifact hash manifest only",
                "compute normalized candidate atoms and scores as normalized_atoms @ weights",
                "keep executed trajectory and online selector output equal to DP Top-1 during shadow phase",
                "fail closed to DP Top-1 and explicit no-shadow log on any contract violation",
            ],
        },
        "static_review_requirements": [
            "prove no shadow index is routed into executed trajectory output",
            "prove no candidate row is created, appended, deleted, blended, or rewritten",
            "prove scoring remains score_k(w)=a_k^T w over fixed current-tick candidate atoms",
        ],
        "forbidden_implementation_paths": [
            "modifying, retraining, or tuning Diffusion Planner",
            "claiming deployability, safety benefit, or CAMP superiority from this plan",
        ],
        "final_decision": {
            "status": module.SOURCE_PLAN_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": module.SOURCE_AUTHORIZED_NEXT_WORK,
            "default_off_shadow_selector_implementation_plan_ready": True,
            "default_off_shadow_selector_implementation_static_contract_review_authorized": True,
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


def _integration_source(*, missing_argmin: bool = False) -> str:
    argmin = "" if missing_argmin else "selected_index = int(np.argmin(selection_scores))"
    return f"""
class CAMPSelectionResult:
    pass

class CAMPSelector:
    pass

def load_dp_camp_atom_scales(path):
    return path

scores = normalized @ weights
{argmin}
selected_trajectory=candidates[selected_index].copy()
"""


def _runner_source() -> str:
    return """
PAPER_FAITHFUL_BOUNDARY_ERROR = "boundary"
def _validate_paper_faithful_boundary(args):
    return None
def _dp_camp_finite_candidate_contract():
    return "argmin over finite feasible candidates"
parser.add_argument("--camp_selector_mode", choices=("top1", "static"))
mode = "top1"
payload = {"executed_output_policy": "dp_top1"}
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
    missing_argmin: bool = False,
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
                f"current_v14_status={module.SOURCE_PLAN_STATUS}",
                f"next_work_target={next_work}",
                "",
            ]
        ),
    )
    current_status = _write(
        docs / "diffusion_planner_current_status.md",
        "\n".join(
            [
                f"current_v14_status={module.SOURCE_PLAN_STATUS}",
                f"next_work_target={module.SOURCE_AUTHORIZED_NEXT_WORK}",
                "",
            ]
        ),
    )
    implementation_plan = _write(
        tmp_path / "implementation_plan.json",
        json.dumps(
            _implementation_plan(
                module,
                implementation_authorized=implementation_authorized,
                score_expression=score_expression,
            ),
            indent=2,
        ),
    )
    integration = _write(
        tmp_path / "diffusion_planner.py",
        _integration_source(missing_argmin=missing_argmin),
    )
    runner = _write(tmp_path / "run_diffusion_planner_camp_replay.py", _runner_source())
    benders = _write(tmp_path / "test_benders.py", _benders_source())
    return {
        "implementation_plan_json": implementation_plan,
        "camp_integration_py": integration,
        "replay_runner_py": runner,
        "benders_contract_test_py": benders,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "review",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def test_v14_static_contract_review_passes_but_does_not_implement(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)
    decision = report["final_decision"]

    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert (
        decision["default_off_shadow_selector_implementation_static_contract_review_passed"]
        is True
    )
    assert (
        decision["default_off_shadow_selector_implementation_unit_tests_plan_authorized"]
        is True
    )
    assert decision["default_off_shadow_selector_implementation_authorized"] is False
    assert decision["online_selector_change_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["training_authorized"] is False
    assert decision["replay_execution_authorized"] is False
    assert decision["candidate_generation_authorized"] is False
    assert "dp_top1_runtime_output_contract" in report["static_contract_review"]["contracts"]
    assert (
        kwargs["output_dir"]
        / "default_off_shadow_selector_implementation_static_contract_review.json"
    ).is_file()
    assert (
        kwargs["output_dir"]
        / "default_off_shadow_selector_implementation_static_contract_review.md"
    ).is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_v14_static_contract_review_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    kwargs["enabled"] = False

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "review_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_static_contract_review_authorization_missing"
    )


def test_v14_static_contract_review_rejects_source_implementation_leak(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, implementation_authorized=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "source_implementation_not_authorized" in report["final_decision"]["failed_checks"]


def test_v14_static_contract_review_rejects_score_contract_drift(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, score_expression="score_k(w)=nonlinear(w)")

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "source_plan_score_expression" in report["final_decision"]["failed_checks"]


def test_v14_static_contract_review_rejects_missing_argmin_surface(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, missing_argmin=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "integration_selects_argmin_selection_scores" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_surface_contract_failure"


def test_v14_static_contract_review_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, wrong_eof=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_v14_static_contract_review_markdown_preserves_boundary(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_report(**_fixture(tmp_path, module))

    markdown = module.render_markdown(report)

    assert "Implementation Static Contract Review" in markdown
    assert "Unit-tests plan authorized: `True`" in markdown
    assert "Implementation authorized: `False`" in markdown
    assert "Online selector change authorized: `False`" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "This gate is review-only" in markdown


def test_v14_static_contract_review_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    output_dir = tmp_path / "cli_review"
    argv = [
        "v14-implementation-static-contract-review",
        "--implementation_plan_json",
        str(kwargs["implementation_plan_json"]),
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
        "--enable_v14_default_off_shadow_selector_implementation_static_contract_review",
    ]
    monkeypatch.setattr("sys.argv", argv)

    assert module.main() == 0

    payload = json.loads(
        (
            output_dir
            / "default_off_shadow_selector_implementation_static_contract_review.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["final_decision"]["status"] == module.READY_STATUS
    assert "Static Contract Review" in (
        output_dir
        / "default_off_shadow_selector_implementation_static_contract_review.md"
    ).read_text(encoding="utf-8")
