from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_remediation_implementation_plan import (
    AUTHORIZED_NEXT_WORK as PLAN_AUTHORIZED_NEXT_WORK,
    PLANNED_CONTRACT_TEST,
    PLANNED_ROUTE_TEST,
    PLANNED_SCREEN_SOURCE,
    READY_STATUS as PLAN_READY_STATUS,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_remediation_implementation_static_contract import (
    ALLOWED_NEXT_FILES,
    AUTHORIZED_NEXT_WORK,
    IMPLEMENTATION_PLAN_JSON,
    IMPLEMENTATION_PLAN_MD,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_STEPS,
    REQUIRED_TESTS,
    build_report,
    main,
    render_markdown,
)


CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={PLAN_READY_STATUS}
authorized_next_work={PLAN_AUTHORIZED_NEXT_WORK}
implementation_code_edit_authorized=False
candidate_generation_execution_authorized=False
training_execution_authorized=False
dp_modification_authorized=False
"""


def _plan_payload(
    *,
    status: str = PLAN_READY_STATUS,
    authorized_next_work: str = PLAN_AUTHORIZED_NEXT_WORK,
    missing_file: str | None = None,
    missing_step: str | None = None,
    missing_test: str | None = None,
    no_dp_import: bool = True,
    blocked_action: bool = False,
) -> dict[str, object]:
    files = [
        PLANNED_SCREEN_SOURCE,
        PLANNED_ROUTE_TEST,
        PLANNED_CONTRACT_TEST,
    ]
    if missing_file:
        files = [item for item in files if item != missing_file]
    steps = [name for name in REQUIRED_STEPS if name != missing_step]
    tests = [name for name in REQUIRED_TESTS if name != missing_test]
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "remediation_implementation_plan_ready": True,
        "remediation_implementation_static_contract_review_authorized": True,
        "implementation_code_edit_authorized": False,
        "candidate_generation_execution_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["candidate_generation_execution_authorized"] = True
    return {
        "analysis": {
            "math_boundary": (
                "preserve score_k(w)=a_k^T w and simplex/CVaR/L2 while "
                "keeping DP fixed"
            )
        },
        "final_decision": decision,
        "remediation_implementation_plan": {
            "selection_type": (
                "residual_comfort_failure_diagnostic_remediation_"
                "implementation_plan_only"
            ),
            "authorized_next_work": PLAN_AUTHORIZED_NEXT_WORK,
            "implementation_scope": {
                "planned_files": files,
                "default_off": True,
                "report_only_until_execution_gate": True,
                "current_tick_finite_candidate_features_only": True,
                "preserve_candidate_ordering": True,
                "preserve_candidate0": True,
                "no_candidate_mutation": True,
                "no_selected_index_mutation": True,
                "no_fallback_mutation": True,
                "no_online_selector_change": True,
                "no_deployed_atom_schema_change": True,
                "no_dp_import": no_dp_import,
                "no_reward_recompute": True,
                "no_tracker_recompute": True,
            },
            "implementation_steps": [
                {"name": name, "purpose": "plan", "contract": "contract"}
                for name in steps
            ],
            "required_tests": tests,
            "static_review_requirements": [
                "prove default behavior and candidate0 ordering remain unchanged",
                "prove report-only descriptor payload cannot alter candidates, scores, selected index, fallback, online selector, or deployed atom schema",
                "prove any later atom proposal must be nonnegative or legal hinge/signed-split",
                "prove score_k(w)=a_k^T w and the convex simplex/CVaR/L2 master remain unchanged",
                "prove no DP import, reward recompute, tracker recompute, DP code, DP weights, DP config, or DP invocation change is required",
                "prove candidate generation execution, fixed-snapshot screen rerun, replay, Full36, formal seeds 11/12/13, CAMP retraining, promotion, and claims remain unauthorized",
            ],
            "blocked_boundaries": [
                "implementation code edits are not authorized in this plan gate",
                "candidate generation execution is not authorized",
                "fixed-snapshot candidate generation and screen rerun are not authorized",
                "formal seeds 11/12/13 remain frozen and unused",
                "no safety-benefit claim or CAMP-over-DP-Top-1 claim is authorized",
            ],
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    markdown_text: str = "# Residual Comfort Remediation Implementation Plan\n",
) -> tuple[Path, Path]:
    root = tmp_path / "implementation_plan"
    audit = tmp_path / "audit.md"
    root.mkdir()
    (root / IMPLEMENTATION_PLAN_JSON).write_text(
        json.dumps(payload or _plan_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / IMPLEMENTATION_PLAN_MD).write_text(markdown_text, encoding="utf-8")
    audit.write_text(audit_text if audit_text is not None else _audit_text(), encoding="utf-8")
    return audit, root


def _build(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    dp_head: str = EXPECTED_DP_HEAD,
) -> dict:
    audit, root = _write_inputs(tmp_path, audit_text=audit_text, payload=payload)
    return build_report(
        implementation_plan_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_residual_comfort_remediation_implementation_static_contract_complete(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["remediation_implementation_only_authorized"] is True
    assert tuple(decision["next_gate_allowed_files"]) == ALLOWED_NEXT_FILES
    assert decision["next_gate_implementation_code_edit_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False


def test_residual_comfort_remediation_implementation_static_contract_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_residual_comfort_remediation_implementation_static_contract_rejects_missing_gate(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_authorizes_static_review" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_implementation_static_contract_rejects_missing_file(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_plan_payload(missing_file=PLANNED_ROUTE_TEST))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "contract_allowed_files_exact" in report["final_decision"]["failed_checks"]


def test_residual_comfort_remediation_implementation_static_contract_rejects_missing_step(
    tmp_path: Path,
) -> None:
    missing = "command_jerk_descriptor_payload"
    report = _build(tmp_path, payload=_plan_payload(missing_step=missing))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert f"contract_step_{missing}" in report["final_decision"]["failed_checks"]


def test_residual_comfort_remediation_implementation_static_contract_rejects_missing_test(
    tmp_path: Path,
) -> None:
    missing = "test_residual_comfort_remediation_report_only_descriptor_payload"
    report = _build(tmp_path, payload=_plan_payload(missing_test=missing))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert f"contract_test_{missing}" in report["final_decision"]["failed_checks"]


def test_residual_comfort_remediation_implementation_static_contract_rejects_dp_import(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_plan_payload(no_dp_import=False))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "contract_no_dp_import" in report["final_decision"]["failed_checks"]


def test_residual_comfort_remediation_implementation_static_contract_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_plan_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_residual_comfort_remediation_implementation_static_contract_markdown_boundaries(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Implementation Static Contract Review" in markdown
    assert PLANNED_SCREEN_SOURCE in markdown
    assert PLANNED_ROUTE_TEST in markdown
    assert "current gate does not edit implementation code" in markdown
    assert "candidate generation execution" in markdown
    assert "formal seeds" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "DP modification" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown


def test_residual_comfort_remediation_implementation_static_contract_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "static_review.json"
    output_md = tmp_path / "out" / "static_review.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "review",
            "--implementation_plan_root",
            str(root),
            "--audit_path",
            str(audit),
            "--camp_head",
            CAMP_COMMIT,
            "--camp_origin_main",
            CAMP_COMMIT,
            "--dp_head",
            EXPECTED_DP_HEAD,
            "--label",
            "cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")
    assert report["analysis"]["label"] == "cli"
    assert report["final_decision"]["status"] == READY_STATUS
    assert markdown.startswith(
        "# Residual Comfort Remediation Implementation Static Contract Review"
    )
