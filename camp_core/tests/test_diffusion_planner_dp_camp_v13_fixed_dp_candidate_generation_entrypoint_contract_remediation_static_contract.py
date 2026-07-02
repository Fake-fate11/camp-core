from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_static_contract import (
    ANALYSIS_FALSE_FLAGS,
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    FUTURE_IMPLEMENTATION_TARGET,
    PASS_STATUS,
    PLAN_DECISION_FALSE_FLAGS,
    PLAN_READY_STATUS,
    PLAN_SCHEMA_VERSION,
    REJECT_STATUS,
    REQUIRED_CONTRACT_CHANGES,
    SCHEMA_VERSION,
    STATIC_REVIEW_SCRIPT,
    STATIC_REVIEW_TEST,
    ZERO_OVERLAP_KEYS,
    build_report,
    main,
)


CAMP_HEAD = "0931abcf5f8f5cdf6c855e11d3bb0c721bcee83c"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_entrypoint_contract_remediation_plan_ready"
)
SCORE_EXPRESSION = "score_k(w)=a_k^T w"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _plan(
    path: Path,
    dp_repo: Path,
    *,
    mutation: Any | None = None,
) -> Path:
    decision = {
        "status": PLAN_READY_STATUS,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "entrypoint_contract_remediation_plan_ready": True,
        "entrypoint_contract_remediation_static_contract_review_authorized_next": True,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }
    for flag in PLAN_DECISION_FALSE_FLAGS:
        decision[flag] = False
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "analysis": {
            "plan_only": True,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
        },
        "entrypoint_contract_remediation_plan": {
            "failure_class": "missing_fixed_dp_candidate_generation_entrypoint",
            "missing_entrypoint_path": str(
                dp_repo / "tools" / "camp_fixed_candidate_generation.py"
            ),
            "remediation_scope": "CAMP-owned entrypoint contract only",
            "dp_repo_modification_allowed": False,
            "dp_config_weight_checkpoint_change_allowed": False,
            "future_static_review_script": STATIC_REVIEW_SCRIPT,
            "future_static_review_test": STATIC_REVIEW_TEST,
            "future_implementation_target": FUTURE_IMPLEMENTATION_TARGET,
            "required_contract_changes": list(REQUIRED_CONTRACT_CHANGES),
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
            "next_gate_is_static_review_only": True,
            "execution_authorized_by_this_gate": False,
        },
        "final_decision": decision,
    }
    for flag in ANALYSIS_FALSE_FLAGS:
        payload["analysis"][flag] = False
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _plan_script(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "FUTURE_STATIC_REVIEW_SCRIPT",
                "entrypoint_contract_remediation_static_contract.py",
                FUTURE_IMPLEMENTATION_TARGET,
                "entrypoint_contract_remediation_static_contract_review_authorized_next",
                "",
            ]
        ),
    )


def _plan_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "test_entrypoint_contract_remediation_plan_authorizes_static_review_only",
                "entrypoint_contract_remediation_static_contract_review_authorized_next",
                "FUTURE_IMPLEMENTATION_TARGET",
                "",
            ]
        ),
    )


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "entrypoint_contract_remediation_static_contract_review_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _repos(tmp_path: Path, *, missing_entrypoint: bool = True) -> tuple[Path, Path]:
    camp_repo = tmp_path / "camp_core"
    dp_repo = tmp_path / "Diffusion-Planner"
    camp_repo.mkdir()
    dp_repo.mkdir()
    if not missing_entrypoint:
        _write(dp_repo / "tools" / "camp_fixed_candidate_generation.py", "unexpected\n")
    return camp_repo, dp_repo


def _report(
    tmp_path: Path,
    *,
    target: str = AUTHORIZED_CURRENT_WORK,
    missing_entrypoint: bool = True,
    mutation: Any | None = None,
) -> dict[str, Any]:
    camp_repo, dp_repo = _repos(tmp_path, missing_entrypoint=missing_entrypoint)
    return build_report(
        plan_json=_plan(tmp_path / "plan.json", dp_repo, mutation=mutation),
        plan_artifact_dir=tmp_path,
        plan_script=_plan_script(tmp_path / "plan.py"),
        plan_test=_plan_test(tmp_path / "test_plan.py"),
        static_review_script=Path(
            "scripts/integrations/review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_static_contract.py"
        ),
        static_review_test=Path(
            "camp_core/tests/test_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_static_contract.py"
        ),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_entrypoint_remediation_static_contract_accepts_plan(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == PASS_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["entrypoint_contract_remediation_static_contract_review_passed"] is True
    assert (
        decision["entrypoint_contract_remediation_implementation_plan_authorized_next"]
        is True
    )
    assert decision["entrypoint_contract_remediation_implementation_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert report["static_contract_review"]["zero_overlap_contract"]["candidate_tensor_hash"]
    assert (
        report["static_contract_review"]["entrypoint_contract"][
            "future_implementation_target"
        ]
        == FUTURE_IMPLEMENTATION_TARGET
    )


def test_entrypoint_remediation_static_contract_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_target_authorizes_static_review" in report["final_decision"][
        "failed_checks"
    ]


def test_entrypoint_remediation_static_contract_rejects_action_leak(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["final_decision"]["training_preflight_authorized_next"] = True

    report = _report(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_no_action_boundary_false" in report["final_decision"]["failed_checks"]


def test_entrypoint_remediation_static_contract_rejects_missing_zero_overlap_key(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["entrypoint_contract_remediation_plan"]["required_zero_overlap_keys"].remove(
            "record_identity"
        )

    report = _report(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "zero_overlap_keys_complete" in report["final_decision"]["failed_checks"]


def test_entrypoint_remediation_static_contract_rejects_if_dp_entrypoint_exists(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, missing_entrypoint=False)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "missing_dp_entrypoint_still_missing" in report["final_decision"][
        "failed_checks"
    ]


def test_entrypoint_remediation_static_contract_main_writes_outputs(
    tmp_path: Path,
) -> None:
    camp_repo, dp_repo = _repos(tmp_path)
    output_json = tmp_path / "review.json"
    output_md = tmp_path / "review.md"

    exit_code = main(
        [
            "--plan_json",
            str(_plan(tmp_path / "plan.json", dp_repo)),
            "--plan_artifact_dir",
            str(tmp_path),
            "--plan_script",
            str(_plan_script(tmp_path / "plan.py")),
            "--plan_test",
            str(_plan_test(tmp_path / "test_plan.py")),
            "--static_review_script",
            "scripts/integrations/review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_static_contract.py",
            "--static_review_test",
            "camp_core/tests/test_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_static_contract.py",
            "--v13_audit_md",
            str(_audit(tmp_path / "audit.md")),
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

    assert camp_repo.exists()
    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == PASS_STATUS
    assert FUTURE_IMPLEMENTATION_TARGET in output_md.read_text(encoding="utf-8")
