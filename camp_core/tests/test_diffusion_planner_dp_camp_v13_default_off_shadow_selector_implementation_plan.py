from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_default_off_shadow_selector_implementation import (
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


CAMP_HEAD = "3c101838f73d4e143ce6fc4357b3241a1e4a2034"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def _static_contract_plan(
    *,
    implementation_authorized: bool = False,
    score_expression: str = "score_k(w)=a_k^T w",
) -> dict[str, object]:
    return {
        "static_contract_plan": {
            "status": "plan_ready_no_implementation",
            "selector_phase": "default_off_shadow_only",
            "runtime_effect": "must_log_shadow_decision_without changing DP top1 output",
            "candidate_count": 8,
            "score_expression": score_expression,
            "selection_rule": "argmin_k score_k(w) over finite candidate rows",
            "default_off_required": True,
            "trajectory_mutation_authorized": False,
            "postselection_authorized": False,
            "fail_closed_policy": (
                "on any missing artifact, K drift, nonfinite value, or source "
                "mismatch, emit DP top1 and log no shadow selection"
            ),
        },
        "final_decision": {
            "status": "dp_camp_v13_default_off_shadow_selector_static_contract_plan_ready",
            "passed": True,
            "authorized_next_work": (
                "dp_camp_v13_default_off_shadow_selector_implementation_plan_only"
            ),
            "static_contract_plan_ready": True,
            "default_off_shadow_selector_implementation_plan_authorized": True,
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
            "production_selector_change_authorized": False,
            "failed_checks": [],
        },
    }


def _integration_source() -> str:
    return """
class CAMPSelector:
    pass

scores = normalized @ weights
selected_index = int(np.argmin(selection_scores))
selected_trajectory=candidates[selected_index].copy()
"""


def _runner_source() -> str:
    return """
PAPER_FAITHFUL_BOUNDARY_ERROR = "boundary"
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


def _audit_source(*, missing_next_target: bool = False) -> str:
    next_target = (
        "next_work_target=dp_camp_v13_default_off_shadow_selector_implementation_plan_only"
    )
    if missing_next_target:
        next_target = "next_work_target=old_scope"
    return f"""
online_selector_change_authorized=False
{next_target}
"""


def _write_inputs(
    tmp_path: Path,
    *,
    implementation_authorized: bool = False,
    score_expression: str = "score_k(w)=a_k^T w",
    missing_next_target: bool = False,
) -> dict[str, Path]:
    paths = {
        "static_contract_plan_json": tmp_path / "static_contract_plan.json",
        "camp_integration_py": tmp_path / "diffusion_planner.py",
        "replay_runner_py": tmp_path / "run_replay.py",
        "benders_contract_test_py": tmp_path / "test_benders.py",
        "v13_audit_md": tmp_path / "audit.md",
    }
    paths["static_contract_plan_json"].write_text(
        json.dumps(
            _static_contract_plan(
                implementation_authorized=implementation_authorized,
                score_expression=score_expression,
            )
        ),
        encoding="utf-8",
    )
    paths["camp_integration_py"].write_text(_integration_source(), encoding="utf-8")
    paths["replay_runner_py"].write_text(_runner_source(), encoding="utf-8")
    paths["benders_contract_test_py"].write_text(_benders_source(), encoding="utf-8")
    paths["v13_audit_md"].write_text(
        _audit_source(missing_next_target=missing_next_target),
        encoding="utf-8",
    )
    return paths


def _report(tmp_path: Path) -> dict[str, object]:
    return build_report(
        **_write_inputs(tmp_path),
        current_camp_head=CAMP_HEAD,
        current_dp_head=DP_HEAD,
        enabled=True,
    )


def test_implementation_plan_ready_but_does_not_implement(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["default_off_shadow_selector_implementation_plan_ready"] is True
    assert (
        decision[
            "default_off_shadow_selector_implementation_static_contract_review_authorized"
        ]
        is True
    )
    assert decision["default_off_shadow_selector_implementation_authorized"] is False
    assert decision["online_selector_change_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert report["implementation_plan"]["selection_rule"] == (
        "shadow_selected_index = argmin_k score_k(w)"
    )


def test_implementation_plan_is_default_off(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    report = build_report(
        static_contract_plan_json=missing,
        camp_integration_py=missing,
        replay_runner_py=missing,
        benders_contract_test_py=missing,
        v13_audit_md=missing,
        current_camp_head=CAMP_HEAD,
        current_dp_head=DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["plan_checks"] == []


def test_implementation_plan_rejects_source_implementation_leak(
    tmp_path: Path,
) -> None:
    report = build_report(
        **_write_inputs(tmp_path, implementation_authorized=True),
        current_camp_head=CAMP_HEAD,
        current_dp_head=DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "source_static_contract_default_off_shadow_selector_implementation_authorized_false"
        in report["final_decision"]["failed_checks"]
    )


def test_implementation_plan_rejects_score_contract_drift(tmp_path: Path) -> None:
    report = build_report(
        **_write_inputs(tmp_path, score_expression="score_k(w)=nonlinear(w)"),
        current_camp_head=CAMP_HEAD,
        current_dp_head=DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_contract_score_expression" in report["final_decision"]["failed_checks"]


def test_implementation_plan_requires_current_audit_target(tmp_path: Path) -> None:
    report = build_report(
        **_write_inputs(tmp_path, missing_next_target=True),
        current_camp_head=CAMP_HEAD,
        current_dp_head=DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_authorizes_current_plan_only" in report["final_decision"][
        "failed_checks"
    ]


def test_implementation_plan_markdown_preserves_boundary(tmp_path: Path) -> None:
    markdown = render_markdown(_report(tmp_path))

    assert "Default-Off Shadow Selector Implementation Plan" in markdown
    assert "Implementation authorized: `False`" in markdown
    assert "Online selector change authorized: `False`" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "This gate is plan-only" in markdown


def test_implementation_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _write_inputs(tmp_path)
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    argv = [
        "v13-implementation-plan",
        "--current_camp_head",
        CAMP_HEAD,
        "--current_dp_head",
        DP_HEAD,
        "--enable_v13_default_off_shadow_selector_implementation_plan",
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
    assert "Implementation Plan" in output_md.read_text(encoding="utf-8")
