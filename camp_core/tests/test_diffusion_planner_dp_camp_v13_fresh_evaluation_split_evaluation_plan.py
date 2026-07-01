from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_fresh_evaluation_split_evaluation import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    SCHEMA_VERSION,
    STATIC_REVIEW_FALSE_FLAGS,
    build_report,
    main,
)


CAMP_HEAD = "427dcd8c63c08e3e84b171bf65ef5fccc0639f85"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_static_contract_review_passed"
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


def _preflight_payload(*, mutation: Any | None = None) -> dict[str, Any]:
    payload = {
        "schema_version": "dp_camp_v13_fresh_evaluation_split_preflight_v1",
        "analysis": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
        },
        "preflight_result": {
            "all_required_intersections_zero": True,
            "selected_member_count": 32,
            "candidate_tensor_hash_intersection_count": 0,
            "path_signature_intersection_count": 0,
            "record_identity_intersection_count": 0,
            "split_manifest_root_intersection_count": 0,
        },
        "final_decision": {
            "status": "dp_camp_v13_fresh_evaluation_split_preflight_passed",
            "passed": True,
            "failed_checks": [],
            "failure_class": None,
            "authorized_next_work": (
                "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
                "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
                "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
                "remediation_fresh_evaluation_split_evaluation_static_contract_review_only"
            ),
            "fresh_evaluation_split_evaluation_authorized_next": True,
            "training_preflight_authorized_next": False,
            "training_execution_authorized_next": False,
            "replay_execution_authorized_next": False,
            "fixed_dp_candidate_generation_authorized_next": False,
            "candidate_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }
    if mutation is not None:
        mutation(payload)
    return payload


def _static_review_payload(*, mutation: Any | None = None) -> dict[str, Any]:
    decision = {
        "status": "dp_camp_v13_fresh_evaluation_split_evaluation_static_contract_review_passed",
        "passed": True,
        "failed_checks": [],
        "authorized_current_work": (
            "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
            "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
            "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
            "remediation_fresh_evaluation_split_evaluation_static_contract_review_only"
        ),
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "fresh_evaluation_split_evaluation_static_contract_review_passed": True,
        "fresh_evaluation_split_evaluation_plan_authorized_next": True,
    }
    decision.update({flag: False for flag in STATIC_REVIEW_FALSE_FLAGS})
    payload = {
        "schema_version": "dp_camp_v13_fresh_evaluation_split_evaluation_static_contract_review_v1",
        "analysis": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
        },
        "preflight_result": {
            "all_required_intersections_zero": True,
            "selected_member_count": 32,
        },
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload)
    return payload


def _artifact_common(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _write(root / "HEADS", _heads())
    _write(root / "COMMAND", "python plan source\n")
    _write(root / "run.exit", "0\n")
    _write(root / "stdout.txt", "{}\n")
    _write(root / "stderr.txt", "")
    _write(root / "SHA256SUMS.artifact", "0" * 64 + "  HEADS\n")
    _write(root / "SHA256SUMS_artifact.check.exit", "0\n")
    _write(root / "SHA256SUMS_artifact.check.stdout", "HEADS: OK\n")
    _write(root / "SHA256SUMS_artifact.check.stderr", "")


def _static_artifact(root: Path, *, mutation: Any | None = None) -> Path:
    _artifact_common(root)
    _write_json(
        root / "fresh_evaluation_split_evaluation_static_contract_review.json",
        _static_review_payload(mutation=mutation),
    )
    _write(root / "fresh_evaluation_split_evaluation_static_contract_review.md", "# ok\n")
    return root


def _preflight_artifact(root: Path, *, mutation: Any | None = None) -> Path:
    _artifact_common(root)
    _write_json(
        root / "fresh_evaluation_split_preflight_report.json",
        _preflight_payload(mutation=mutation),
    )
    _write(root / "fresh_evaluation_split_preflight_report.md", "# ok\n")
    return root


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "fresh_evaluation_split_evaluation_plan_authorized_next=True",
        "fresh_evaluation_split_evaluation_execution_authorized_next=False",
        "all_required_intersections_zero=True",
        *[f"{flag}=False" for flag in AUDIT_FALSE_FLAGS],
        f"next_work_target={target}",
        "",
    ]
    return _write(path, "\n".join(lines))


def _report(
    tmp_path: Path,
    *,
    static_mutation: Any | None = None,
    preflight_mutation: Any | None = None,
    audit_target: str = AUTHORIZED_CURRENT_WORK,
) -> dict[str, Any]:
    return build_report(
        static_review_artifact_dir=_static_artifact(
            tmp_path / "static",
            mutation=static_mutation,
        ),
        preflight_artifact_dir=_preflight_artifact(
            tmp_path / "preflight",
            mutation=preflight_mutation,
        ),
        v13_audit_md=_audit(tmp_path / "audit.md", target=audit_target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_fresh_evaluation_split_evaluation_plan_ready_but_does_not_execute(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    plan = report["fresh_evaluation_split_evaluation_plan"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fresh_evaluation_split_evaluation_implementation_plan_authorized_next"] is True
    assert decision["fresh_evaluation_split_evaluation_execution_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert plan["evaluation_execution_by_this_gate"] is False
    assert plan["source_requirements"]["selected_member_count"] == 32
    assert plan["source_requirements"]["all_required_intersections_zero"] is True
    assert plan["evaluation_contract"]["shadow_selected_index_only"] is True
    assert plan["evaluation_contract"]["training_input_from_future_evaluation"] is False
    assert plan["math_boundary"]["score_expression"] == "score_k(w)=a_k^T w"
    assert plan["math_boundary"]["simplex_cvar_l2_master_remains_convex"] is True


def test_fresh_evaluation_split_evaluation_plan_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _report(tmp_path, audit_target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_fresh_evaluation_split_evaluation_plan_rejects_training_leak(tmp_path: Path) -> None:
    def leak(payload: dict[str, Any]) -> None:
        payload["final_decision"]["training_execution_authorized_next"] = True

    report = _report(tmp_path, static_mutation=leak)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "static_review_blocks_training_execution_authorized_next"
        in report["final_decision"]["failed_checks"]
    )


def test_fresh_evaluation_split_evaluation_plan_rejects_nonzero_overlap(tmp_path: Path) -> None:
    def overlap(payload: dict[str, Any]) -> None:
        payload["preflight_result"]["all_required_intersections_zero"] = False
        payload["preflight_result"]["record_identity_intersection_count"] = 1

    report = _report(tmp_path, preflight_mutation=overlap)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "preflight_all_intersections_zero" in report["final_decision"]["failed_checks"]
    assert "preflight_zero_record_identity_intersection_count" in report["final_decision"]["failed_checks"]


def test_fresh_evaluation_split_evaluation_plan_main_writes_outputs(tmp_path: Path) -> None:
    output_json = tmp_path / "out" / "fresh_evaluation_split_evaluation_plan.json"
    output_md = tmp_path / "out" / "fresh_evaluation_split_evaluation_plan.md"
    static_dir = _static_artifact(tmp_path / "static")
    preflight_dir = _preflight_artifact(tmp_path / "preflight")
    audit = _audit(tmp_path / "audit.md")

    exit_code = main(
        [
            "--static_review_artifact_dir",
            str(static_dir),
            "--preflight_artifact_dir",
            str(preflight_dir),
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
    assert payload["fresh_evaluation_split_evaluation_plan"]["plan_only_gate"] is True
    assert "plan-only gate does not execute evaluation" in output_md.read_text(
        encoding="utf-8"
    )
