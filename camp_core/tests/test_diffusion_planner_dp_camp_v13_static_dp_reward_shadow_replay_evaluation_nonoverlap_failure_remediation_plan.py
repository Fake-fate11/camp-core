from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_failure_remediation import (
    ATTRIBUTED_STATUS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "07fff1d61d2e0c3efc888d823c605a3140ccd1e3"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _attribution(path: Path, *, passed: bool = True) -> Path:
    final_status = ATTRIBUTED_STATUS if passed else f"{ATTRIBUTED_STATUS}_incomplete"
    return _write(
        path,
        json.dumps(
            {
                "final_decision": {
                    "status": final_status,
                    "passed": passed,
                    "failed_checks": [] if passed else ["record_identity_intersection_full"],
                    "authorized_next_work": AUTHORIZED_CURRENT_WORK,
                },
                "attribution": {
                    "failure_class": "evaluation_set_overlaps_training_manifest_recovered_prior_source",
                    "primary_cause": "candidate, path, and record identity overlap",
                    "current_evaluation_is_not_independent_holdout": True,
                    "raw_prior_logs_missing_but_recovered_registry_authoritative": True,
                    "training_summary_only_overlap_is_insufficient_for_this_case": True,
                },
                "overlap_evidence": {
                    "records_total": 3200,
                    "training_manifest_log_count": 416,
                    "training_missing_log_count": 96,
                    "candidate_hash_intersection_count": 2140,
                    "path_signature_intersection_count": 32,
                    "record_identity_intersection_count": 3200,
                    "candidate_tensor_eval_hashes_in_previous_rate": 1.0,
                },
            }
        ),
    )


def _audit(path: Path, *, current_work: str = AUTHORIZED_CURRENT_WORK) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "current_v13_status=static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_nonoverlap_failure_attributed",
                f"next_work_target={current_work}",
                "training_execution_authorized_by_current_boundary=False",
                "replay_execution_authorized_by_current_boundary=False",
                "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
                "candidate_generation_by_camp_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "",
            ]
        ),
    )


def _report(
    tmp_path: Path,
    *,
    attribution_passed: bool = True,
    current_work: str = AUTHORIZED_CURRENT_WORK,
) -> dict:
    return build_report(
        nonoverlap_failure_attribution_json=_attribution(
            tmp_path / "nonoverlap_failure_attribution.json",
            passed=attribution_passed,
        ),
        v13_audit_md=_audit(tmp_path / "audit.md", current_work=current_work),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_nonoverlap_failure_remediation_plan_accepts_attribution(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["static_contract_review_authorized_next"] is True
    assert decision["training_preflight_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert report["remediation_plan"]["required_static_contracts"][
        "recovered_missing_prior_registry_must_be_loaded"
    ] is True
    assert report["remediation_plan"]["required_static_contracts"][
        "record_identity_intersection_must_be_zero"
    ] is True
    assert report["remediation_plan"]["blocked_by_this_plan"]["training_preflight"] is True
    assert report["analysis"]["score_expression"] == "score_k(w)=a_k^T w"


def test_nonoverlap_failure_remediation_plan_rejects_wrong_audit_scope(tmp_path: Path) -> None:
    report = _report(tmp_path, current_work="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_gate_authorized_by_latest_audit_target" in report["final_decision"][
        "failed_checks"
    ]


def test_nonoverlap_failure_remediation_plan_rejects_failed_attribution(tmp_path: Path) -> None:
    report = _report(tmp_path, attribution_passed=False)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "attribution_passed" in report["final_decision"]["failed_checks"]
    assert "attribution_status_expected" in report["final_decision"]["failed_checks"]


def test_nonoverlap_failure_remediation_plan_main_writes_outputs(tmp_path: Path) -> None:
    attribution = _attribution(tmp_path / "nonoverlap_failure_attribution.json")
    audit = _audit(tmp_path / "audit.md")
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"

    exit_code = main(
        [
            "--nonoverlap_failure_attribution_json",
            str(attribution),
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
    assert json.loads(output_json.read_text(encoding="utf-8"))["final_decision"][
        "status"
    ] == READY_STATUS
    assert READY_STATUS in output_md.read_text(encoding="utf-8")
