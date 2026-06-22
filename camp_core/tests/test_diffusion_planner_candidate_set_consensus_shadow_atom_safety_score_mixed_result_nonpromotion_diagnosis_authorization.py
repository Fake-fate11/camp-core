from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.authorize_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion_diagnosis import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _plan_payload(*, blocked_action: bool = False) -> dict[str, object]:
    return {
        "final_decision": {
            "status": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "mixed_result_nonpromotion_diagnosis_plan_ready"
            ),
            "passed": True,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "mixed_result_nonpromotion_diagnosis_authorization_only"
            ),
            "mixed_result_nonpromotion_diagnosis_plan_ready": True,
            "mixed_result_nonpromotion_diagnosis_authorization_gate_authorized": True,
            "mixed_result_nonpromotion_diagnosis_authorized": False,
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": blocked_action,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "camp_retraining_authorized": False,
            "training_execution_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "diagnosis_plan": {
            "executes_diagnosis_now": False,
            "requires_new_replay": False,
            "requires_atom_promotion": False,
            "requires_online_selector_change": False,
            "requires_dp_modification": False,
            "diagnostic_questions": ["question"],
            "accept_criteria": [
                "formal seed strings remain absent",
                "diagnosis remains read-only with no online selector effect",
            ],
            "reject_criteria": [
                "any training, promotion, or DP modification is required",
            ],
        },
    }


def _review_payload() -> dict[str, object]:
    return {
        "final_decision": {
            "status": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "evaluation_result_review_ready"
            ),
            "passed": True,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "mixed_result_nonpromotion_diagnosis_plan_only"
            ),
            "safety_score_evaluation_result_review_ready": True,
            "result_classification": "mixed_nonpromotion",
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "camp_retraining_authorized": False,
            "training_execution_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def _execution_payload() -> dict[str, object]:
    return {
        "final_decision": {
            "status": "candidate_set_consensus_shadow_atom_safety_score_evaluation_ready",
            "passed": True,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "evaluation_result_review_only"
            ),
            "safety_score_evaluation_ready": True,
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "camp_retraining_authorized": False,
            "training_execution_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "evaluation_summary": {
            "records": 60,
            "valid_records": 60,
            "outcome_available_records": 60,
            "formal_seed_log_count": 0,
            "max_changed_records": 11,
        },
    }


def _write_artifact(root: Path, json_name: str, md_name: str, payload: dict[str, object]) -> None:
    root.mkdir(exist_ok=True)
    (root / json_name).write_text(json.dumps(payload), encoding="utf-8")
    (root / md_name).write_text("# artifact\n", encoding="utf-8")
    (root / "COMMAND.log").write_text("command\n", encoding="utf-8")
    (root / "COMMAND.err").write_text("", encoding="utf-8")
    (root / "EXIT_CODE").write_text("0\n", encoding="utf-8")
    (root / "HEADS.txt").write_text(
        f"CAMP_HEAD=head\nDP_HEAD={EXPECTED_DP_HEAD}\n",
        encoding="utf-8",
    )
    _write_sha256sums(root, (json_name, md_name, "COMMAND.log", "COMMAND.err", "EXIT_CODE", "HEADS.txt"))


def _write_roots(tmp_path: Path) -> tuple[Path, Path, Path]:
    plan = tmp_path / "plan"
    review = tmp_path / "review"
    execution = tmp_path / "execution"
    _write_artifact(
        plan,
        "candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion_diagnosis_plan.json",
        "candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion_diagnosis_plan.md",
        _plan_payload(),
    )
    _write_artifact(
        review,
        "candidate_set_consensus_shadow_atom_safety_score_evaluation_result_review.json",
        "candidate_set_consensus_shadow_atom_safety_score_evaluation_result_review.md",
        _review_payload(),
    )
    _write_artifact(
        execution,
        "candidate_set_consensus_shadow_atom_safety_score_evaluation_retry_execution.json",
        "candidate_set_consensus_shadow_atom_safety_score_evaluation_retry_execution.md",
        _execution_payload(),
    )
    return plan, review, execution


def test_mixed_result_nonpromotion_diagnosis_authorization_ready(tmp_path: Path) -> None:
    plan, review, execution = _write_roots(tmp_path)

    report = build_report(
        plan_root=plan,
        result_review_root=review,
        execution_root=execution,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["mixed_result_nonpromotion_diagnosis_execution_authorized"] is True
    assert decision["mixed_result_nonpromotion_diagnosis_executed"] is False
    assert decision["safety_benefit_evidence"] is False
    assert decision["atom_promotion_authorized"] is False


def test_mixed_result_nonpromotion_diagnosis_authorization_rejects_sha_mismatch(
    tmp_path: Path,
) -> None:
    plan, review, execution = _write_roots(tmp_path)
    (plan / "candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion_diagnosis_plan.md").write_text(
        "# mutated\n",
        encoding="utf-8",
    )

    report = build_report(
        plan_root=plan,
        result_review_root=review,
        execution_root=execution,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_mixed_result_nonpromotion_diagnosis_authorization_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    plan, review, execution = _write_roots(tmp_path)

    report = build_report(
        plan_root=plan,
        result_review_root=review,
        execution_root=execution,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_mixed_result_nonpromotion_diagnosis_authorization_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    plan, review, execution = _write_roots(tmp_path)
    _write_artifact(
        plan,
        "candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion_diagnosis_plan.json",
        "candidate_set_consensus_shadow_atom_safety_score_mixed_result_nonpromotion_diagnosis_plan.md",
        _plan_payload(blocked_action=True),
    )

    report = build_report(
        plan_root=plan,
        result_review_root=review,
        execution_root=execution,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_mixed_result_nonpromotion_diagnosis_authorization_markdown(tmp_path: Path) -> None:
    plan, review, execution = _write_roots(tmp_path)
    report = build_report(
        plan_root=plan,
        result_review_root=review,
        execution_root=execution,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    markdown = render_markdown(report)

    assert "Diagnosis Authorization" in markdown
    assert "Diagnosis execution authorized: `True`" in markdown
    assert "Diagnosis executed: `False`" in markdown
    assert "classical Benders" in markdown


def test_mixed_result_nonpromotion_diagnosis_authorization_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, review, execution = _write_roots(tmp_path)
    output_json = tmp_path / "authorization.json"
    output_md = tmp_path / "authorization.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "mixed-result-nonpromotion-diagnosis-authorization",
            "--plan_root",
            str(plan),
            "--result_review_root",
            str(review),
            "--execution_root",
            str(execution),
            "--camp_head",
            "abc",
            "--camp_origin_main",
            "abc",
            "--dp_head",
            EXPECTED_DP_HEAD,
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Diagnosis Authorization" in output_md.read_text(encoding="utf-8")
