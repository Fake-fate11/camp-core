from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fresh_evaluation_split_evaluation_post_implementation_static_contract import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    CURRENT_AUDIT_FALSE_FLAGS,
    FIXED_DP_HEAD,
    LATEST_AUDIT_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_SCRIPT_TERMS,
    REQUIRED_TEST_TERMS,
    SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "4c787118b7adda552c92880a81db3dbe12c1509e"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _script(path: Path, *, missing_term: str | None = None) -> Path:
    terms = [term for term in REQUIRED_SCRIPT_TERMS if term != missing_term]
    return _write(path, "\n".join(terms) + "\n")


def _test(path: Path, *, missing_term: str | None = None) -> Path:
    terms = [term for term in REQUIRED_TEST_TERMS if term != missing_term]
    return _write(path, "\n".join(terms) + "\n")


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK, training_leak: bool = False) -> Path:
    lines = [
        f"current_v13_status={LATEST_AUDIT_STATUS}",
        "fresh_evaluation_split_evaluation_implementation_complete=True",
        "fresh_evaluation_split_evaluation_post_implementation_static_contract_review_authorized_next=True",
    ]
    for flag in CURRENT_AUDIT_FALSE_FLAGS:
        value = training_leak and flag == "training_execution_authorized_by_current_boundary"
        lines.append(f"{flag}={value}")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _report(
    tmp_path: Path,
    *,
    missing_script_term: str | None = None,
    missing_test_term: str | None = None,
    audit_target: str = AUTHORIZED_CURRENT_WORK,
    training_leak: bool = False,
) -> dict:
    return build_report(
        evaluator_script_py=_script(tmp_path / "evaluate.py", missing_term=missing_script_term),
        evaluator_test_py=_test(tmp_path / "test_evaluate.py", missing_term=missing_test_term),
        v13_audit_md=_audit(
            tmp_path / "audit.md",
            target=audit_target,
            training_leak=training_leak,
        ),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_fresh_evaluation_split_evaluation_post_implementation_static_contract_passes(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    review = report["static_contract_review"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fresh_evaluation_split_evaluation_execution_authorized_next"] is True
    assert decision["training_preflight_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert review["must_remain_default_off_shadow"] is True
    assert review["executed_trajectory_change_allowed"] is False
    assert review["score_expression"] == "score_k(w)=a_k^T w"


def test_fresh_evaluation_split_evaluation_post_implementation_static_contract_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _report(tmp_path, audit_target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None
    assert report["final_decision"]["fresh_evaluation_split_evaluation_execution_authorized_next"] is False


def test_fresh_evaluation_split_evaluation_post_implementation_static_contract_rejects_script_drift(tmp_path: Path) -> None:
    report = _report(tmp_path, missing_script_term="DISABLED_STATUS")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "script_required_terms_present" in report["final_decision"]["failed_checks"]
    assert "DISABLED_STATUS" in report["static_contract_review"]["required_script_terms_missing"]


def test_fresh_evaluation_split_evaluation_post_implementation_static_contract_rejects_training_leak(tmp_path: Path) -> None:
    report = _report(tmp_path, training_leak=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "audit_blocks_training_execution_authorized_by_current_boundary"
        in report["final_decision"]["failed_checks"]
    )


def test_fresh_evaluation_split_evaluation_post_implementation_static_contract_main_writes_outputs(tmp_path: Path) -> None:
    script = _script(tmp_path / "evaluate.py")
    test = _test(tmp_path / "test_evaluate.py")
    audit = _audit(tmp_path / "audit.md")
    output_json = tmp_path / "out" / "fresh_evaluation_split_evaluation_post_implementation_static_contract_review.json"
    output_md = tmp_path / "out" / "fresh_evaluation_split_evaluation_post_implementation_static_contract_review.md"

    exit_code = main(
        [
            "--evaluator_script_py",
            str(script),
            "--evaluator_test_py",
            str(test),
            "--v13_audit_md",
            str(audit),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert "authorizes only the read-only fresh evaluation execution" in output_md.read_text(
        encoding="utf-8"
    )
