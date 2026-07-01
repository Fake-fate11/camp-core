from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fresh_evaluation_split_evaluation_implementation_static_contract import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    FUTURE_EVALUATOR_SCRIPT,
    FUTURE_EVALUATOR_TEST,
    READY_STATUS,
    REJECT_STATUS,
    SCHEMA_VERSION,
    SOURCE_FALSE_FLAGS,
    build_report,
    main,
)


CAMP_HEAD = "4b4a830359b41778e0d42cb4dbb9024545e4e6bd"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_implementation_plan_ready"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _heads() -> str:
    return "\n".join(
        [
            f"camp_head={CAMP_HEAD}",
            f"camp_origin_main={CAMP_HEAD}",
            f"dp_head={FIXED_DP_HEAD}",
            "",
        ]
    )


def _source_payload(*, mutation: Any | None = None) -> dict[str, Any]:
    decision = {
        "status": "dp_camp_v13_fresh_evaluation_split_evaluation_implementation_plan_ready",
        "passed": True,
        "failed_checks": [],
        "authorized_current_work": (
            "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
            "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
            "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
            "remediation_fresh_evaluation_split_evaluation_implementation_plan_only"
        ),
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "fresh_evaluation_split_evaluation_implementation_plan_ready": True,
        "fresh_evaluation_split_evaluation_implementation_static_contract_review_authorized_next": True,
    }
    decision.update({flag: False for flag in SOURCE_FALSE_FLAGS})
    payload = {
        "schema_version": "dp_camp_v13_fresh_evaluation_split_evaluation_implementation_plan_v1",
        "implementation_plan": {
            "implementation_execution_by_this_gate": False,
            "evaluation_execution_by_this_gate": False,
            "future_evaluator": {
                "script": FUTURE_EVALUATOR_SCRIPT,
                "test": FUTURE_EVALUATOR_TEST,
                "output_contract": {
                    "shadow_selected_index_only": True,
                    "executed_trajectory_change": False,
                },
            },
            "source_invariants": {
                "selected_member_count": 32,
                "all_required_intersections_zero": True,
            },
            "future_fail_closed_checks": [
                "DP HEAD must equal the fixed TiERIV Diffusion Planner commit",
                "all four zero-overlap intersections must remain zero",
            ],
            "math_boundary": {
                "candidate_operation": "fixed DP candidate reranking only",
                "score_expression": "score_k(w)=a_k^T w",
                "approved_atoms_only": True,
                "nonnegative_simplex_weights_only": True,
                "simplex_cvar_l2_master_remains_convex": True,
            },
        },
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload)
    return payload


def _artifact(root: Path, *, mutation: Any | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _write(root / "HEADS", _heads())
    _write(root / "COMMAND", "python implementation plan\n")
    _write(root / "run.exit", "0\n")
    _write(root / "stdout.txt", "{}\n")
    _write(root / "stderr.txt", "")
    _write_json(
        root / "fresh_evaluation_split_evaluation_implementation_plan.json",
        _source_payload(mutation=mutation),
    )
    _write(root / "fresh_evaluation_split_evaluation_implementation_plan.md", "# ok\n")
    _write(root / "SHA256SUMS.artifact", "0" * 64 + "  HEADS\n")
    _write(root / "SHA256SUMS_artifact.check.exit", "0\n")
    _write(root / "SHA256SUMS_artifact.check.stdout", "HEADS: OK\n")
    _write(root / "SHA256SUMS_artifact.check.stderr", "")
    return root


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "fresh_evaluation_split_evaluation_implementation_static_contract_review_authorized_next=True",
        "fresh_evaluation_split_evaluation_execution_authorized_next=False",
        *[f"{flag}=False" for flag in AUDIT_FALSE_FLAGS],
        f"next_work_target={target}",
        "",
    ]
    return _write(path, "\n".join(lines))


def _report(
    tmp_path: Path,
    *,
    source_mutation: Any | None = None,
    audit_target: str = AUTHORIZED_CURRENT_WORK,
) -> dict[str, Any]:
    return build_report(
        implementation_plan_artifact_dir=_artifact(
            tmp_path / "artifact",
            mutation=source_mutation,
        ),
        v13_audit_md=_audit(tmp_path / "audit.md", target=audit_target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_fresh_evaluation_split_evaluation_implementation_static_contract_passes(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    review = report["static_contract_review"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fresh_evaluation_split_evaluation_implementation_authorized_next"] is True
    assert decision["fresh_evaluation_split_evaluation_execution_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert review["future_implementation_allowed_next"] is True
    assert review["implementation_execution_by_this_gate"] is False
    assert review["evaluation_execution_by_this_gate"] is False
    assert review["must_remain_default_off_shadow"] is True
    assert review["executed_trajectory_change_allowed"] is False
    assert review["math_boundary"]["score_expression"] == "score_k(w)=a_k^T w"


def test_fresh_evaluation_split_evaluation_implementation_static_contract_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _report(tmp_path, audit_target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_fresh_evaluation_split_evaluation_implementation_static_contract_rejects_source_execution_leak(tmp_path: Path) -> None:
    def leak(payload: dict[str, Any]) -> None:
        payload["final_decision"]["training_execution_authorized_next"] = True

    report = _report(tmp_path, source_mutation=leak)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "source_blocks_training_execution_authorized_next"
        in report["final_decision"]["failed_checks"]
    )


def test_fresh_evaluation_split_evaluation_implementation_static_contract_rejects_shadow_contract_drift(tmp_path: Path) -> None:
    def drift(payload: dict[str, Any]) -> None:
        output = payload["implementation_plan"]["future_evaluator"]["output_contract"]
        output["shadow_selected_index_only"] = False

    report = _report(tmp_path, source_mutation=drift)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_shadow_selected_index_only" in report["final_decision"]["failed_checks"]
    assert "review_shadow_default_off" in report["final_decision"]["failed_checks"]


def test_fresh_evaluation_split_evaluation_implementation_static_contract_main_writes_outputs(tmp_path: Path) -> None:
    artifact = _artifact(tmp_path / "artifact")
    audit = _audit(tmp_path / "audit.md")
    output_json = tmp_path / "out" / "fresh_evaluation_split_evaluation_implementation_static_contract_review.json"
    output_md = tmp_path / "out" / "fresh_evaluation_split_evaluation_implementation_static_contract_review.md"

    exit_code = main(
        [
            "--implementation_plan_artifact_dir",
            str(artifact),
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
    assert payload["static_contract_review"]["future_implementation_allowed_next"] is True
    assert "authorizes only future implementation" in output_md.read_text(
        encoding="utf-8"
    )
