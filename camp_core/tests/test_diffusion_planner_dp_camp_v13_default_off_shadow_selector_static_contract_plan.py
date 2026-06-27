from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_default_off_shadow_selector_static_contract import (
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


CAMP_HEAD = "fec07cb7ec9719c335507f70566aac750a1f4c66"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def _preflight(*, selector_promotion: bool = False) -> dict[str, object]:
    return {
        "artifact_manifest": [{"name": f"artifact_{idx}"} for idx in range(10)],
        "static_integration_contract": {
            "status": "preflight_ready_contract_pinned",
            "score_expression": "score_k(w)=a_k^T w",
        },
        "final_decision": {
            "status": "dp_camp_v13_promotion_evidence_package_preflight_ready",
            "passed": True,
            "authorized_next_work": (
                "dp_camp_v13_default_off_shadow_selector_static_integration_contract_plan_only"
            ),
            "failed_checks": [],
            "static_integration_contract_pinned": True,
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
            "production_selector_change_authorized": False,
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
"""


def _benders_source() -> str:
    return """
def test_fixed_candidate_atom_scores_are_affine_in_simplex_weights():
    pass
def test_robust_margin_master_rejects_negative_atom_coefficients():
    pass
"""


def _write_inputs(
    tmp_path: Path,
    *,
    selector_promotion: bool = False,
    missing_argmin: bool = False,
) -> dict[str, Path]:
    paths = {
        "evidence_package_preflight_json": tmp_path / "preflight.json",
        "camp_integration_py": tmp_path / "diffusion_planner.py",
        "replay_runner_py": tmp_path / "run_replay.py",
        "benders_contract_test_py": tmp_path / "test_benders.py",
    }
    paths["evidence_package_preflight_json"].write_text(
        json.dumps(_preflight(selector_promotion=selector_promotion)),
        encoding="utf-8",
    )
    paths["camp_integration_py"].write_text(
        _integration_source(missing_argmin=missing_argmin),
        encoding="utf-8",
    )
    paths["replay_runner_py"].write_text(_runner_source(), encoding="utf-8")
    paths["benders_contract_test_py"].write_text(_benders_source(), encoding="utf-8")
    return paths


def _report(tmp_path: Path) -> dict[str, object]:
    return build_report(
        **_write_inputs(tmp_path),
        current_camp_head=CAMP_HEAD,
        current_dp_head=DP_HEAD,
        enabled=True,
    )


def test_static_contract_plan_ready_but_does_not_implement(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["static_contract_plan_ready"] is True
    assert decision["default_off_shadow_selector_implementation_plan_authorized"] is True
    assert decision["default_off_shadow_selector_implementation_authorized"] is False
    assert decision["online_selector_change_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert report["static_contract_plan"]["runtime_effect"] == (
        "must_log_shadow_decision_without changing DP top1 output"
    )


def test_static_contract_plan_is_default_off(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    report = build_report(
        evidence_package_preflight_json=missing,
        camp_integration_py=missing,
        replay_runner_py=missing,
        benders_contract_test_py=missing,
        current_camp_head=CAMP_HEAD,
        current_dp_head=DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["plan_checks"] == []


def test_static_contract_plan_rejects_preflight_promotion_leak(tmp_path: Path) -> None:
    report = build_report(
        **_write_inputs(tmp_path, selector_promotion=True),
        current_camp_head=CAMP_HEAD,
        current_dp_head=DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_preflight_selector_promotion_authorized_false" in report[
        "final_decision"
    ]["failed_checks"]


def test_static_contract_plan_rejects_missing_argmin_surface(tmp_path: Path) -> None:
    report = build_report(
        **_write_inputs(tmp_path, missing_argmin=True),
        current_camp_head=CAMP_HEAD,
        current_dp_head=DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "integration_selects_argmin_selection_scores" in report["final_decision"][
        "failed_checks"
    ]


def test_static_contract_plan_markdown_preserves_boundary(tmp_path: Path) -> None:
    markdown = render_markdown(_report(tmp_path))

    assert "Default-Off Shadow Selector Static Contract Plan" in markdown
    assert "Implementation authorized: `False`" in markdown
    assert "Online selector change authorized: `False`" in markdown
    assert "score_k(w)=a_k^T w" in markdown


def test_static_contract_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _write_inputs(tmp_path)
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    argv = [
        "v13-static-contract-plan",
        "--current_camp_head",
        CAMP_HEAD,
        "--current_dp_head",
        DP_HEAD,
        "--enable_v13_default_off_shadow_selector_static_contract_plan",
        "--output_json",
        str(output_json),
        "--output_md",
        str(output_md),
    ]
    for name, path in paths.items():
        argv.extend([f"--{name}", str(path)])
    monkeypatch.setattr("sys.argv", argv)

    assert main() == 0

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Static Contract Plan" in output_md.read_text(encoding="utf-8")
