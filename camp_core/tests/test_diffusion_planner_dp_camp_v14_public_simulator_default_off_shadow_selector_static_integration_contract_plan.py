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
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_static_integration_contract.py"
)
CAMP_HEAD = "b27188846581c167ea867c498eed55a541a96487"


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_shadow_static_contract_plan", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _preflight(module, *, selector_promotion: bool = False) -> dict:
    return {
        "artifact_manifest": [{"name": f"artifact_{index}"} for index in range(7)],
        "source_summary": {
            "records_total": 3200,
            "training_records": 2914,
            "num_candidates": 8,
            "num_atoms": 9,
        },
        "static_integration_contract": {
            "status": "preflight_ready_contract_pinned",
            "score_expression": module.SCORE_EXPRESSION,
            "simplex_master_convex": True,
            "cvar_master_convex": True,
            "l2_master_convex": True,
        },
        "final_decision": {
            "status": module.SOURCE_PREFLIGHT_STATUS,
            "passed": True,
            "authorized_next_work": module.SOURCE_AUTHORIZED_NEXT_WORK,
            "failed_checks": [],
            "default_off_shadow_selector_contract_plan_authorized": True,
            "selector_promotion_authorized": selector_promotion,
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


def _fixture(tmp_path: Path, module, *, wrong_eof: bool = False, missing_argmin: bool = False) -> dict:
    docs = tmp_path / "docs"
    next_work = "wrong_gate" if wrong_eof else module.SOURCE_AUTHORIZED_NEXT_WORK
    v14_audit = _write(
        docs / "diffusion_planner_v14_iteration_audit.md",
        "\n".join(
            [
                "## Current Section",
                f"current_v14_status={module.SOURCE_PREFLIGHT_STATUS}",
                f"next_work_target={next_work}",
                "",
            ]
        ),
    )
    current_status = _write(
        docs / "diffusion_planner_current_status.md",
        "\n".join(
            [
                f"current_v14_status={module.SOURCE_PREFLIGHT_STATUS}",
                f"next_work_target={module.SOURCE_AUTHORIZED_NEXT_WORK}",
                "",
            ]
        ),
    )
    preflight = _write(
        tmp_path / "promotion_evidence_package_preflight.json",
        json.dumps(_preflight(module), indent=2),
    )
    integration = _write(
        tmp_path / "diffusion_planner.py",
        _integration_source(missing_argmin=missing_argmin),
    )
    runner = _write(tmp_path / "run_diffusion_planner_camp_replay.py", _runner_source())
    benders = _write(tmp_path / "test_benders.py", _benders_source())
    return {
        "evidence_package_preflight_json": preflight,
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


def test_v14_static_contract_plan_ready_but_does_not_implement(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)
    decision = report["final_decision"]

    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["static_contract_plan_ready"] is True
    assert decision["default_off_shadow_selector_implementation_plan_authorized"] is True
    assert decision["default_off_shadow_selector_implementation_authorized"] is False
    assert decision["online_selector_change_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["training_authorized"] is False
    assert decision["replay_execution_authorized"] is False
    assert decision["candidate_generation_authorized"] is False
    assert report["static_contract_plan"]["runtime_effect"] == (
        "must_log_shadow_selected_index_without_changing_dp_top1_output"
    )
    assert (kwargs["output_dir"] / "default_off_shadow_selector_static_integration_contract_plan.json").is_file()
    assert (kwargs["output_dir"] / "default_off_shadow_selector_static_integration_contract_plan.md").is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_v14_static_contract_plan_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    kwargs["enabled"] = False

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "plan_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_static_contract_plan_authorization_missing"
    )


def test_v14_static_contract_plan_rejects_preflight_promotion_leak(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    payload = _preflight(module, selector_promotion=True)
    kwargs["evidence_package_preflight_json"].write_text(json.dumps(payload), encoding="utf-8")

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "source_preflight_selector_promotion_authorized_false" in report["final_decision"]["failed_checks"]


def test_v14_static_contract_plan_rejects_missing_argmin_surface(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, missing_argmin=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "integration_selects_argmin_selection_scores" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_surface_contract_failure"


def test_v14_static_contract_plan_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, wrong_eof=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["status"] == module.REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"
