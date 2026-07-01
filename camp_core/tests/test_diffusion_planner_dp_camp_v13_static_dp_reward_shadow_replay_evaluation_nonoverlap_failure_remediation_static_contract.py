from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.review_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_failure_remediation_static_contract import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    BLOCKED_ACTIONS,
    FIXED_DP_HEAD,
    PASS_STATUS,
    PLAN_READY_STATUS,
    REJECT_STATUS,
    REQUIRED_CONTRACTS,
    build_report,
    main,
)


CAMP_HEAD = "08225c53ef39b634d538b2829513f7a460f893c4"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_plan_ready"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _plan(path: Path, *, missing_contract: str | None = None, leak_action: str | None = None) -> Path:
    required = {name: True for name in REQUIRED_CONTRACTS}
    blocked = {name: True for name in BLOCKED_ACTIONS}
    if missing_contract:
        required[missing_contract] = False
    if leak_action:
        blocked[leak_action] = False
    return _write(
        path,
        json.dumps(
            {
                "analysis": {
                    "read_only_inputs": True,
                    "score_expression": "score_k(w)=a_k^T w",
                },
                "attribution_summary": {
                    "failure_class": "evaluation_set_overlaps_training_manifest_recovered_prior_source",
                    "record_identity_intersection_count": 3200,
                    "candidate_tensor_eval_hashes_in_previous_rate": 1.0,
                },
                "final_decision": {
                    "status": PLAN_READY_STATUS,
                    "passed": True,
                    "failed_checks": [],
                    "authorized_next_work": AUTHORIZED_CURRENT_WORK,
                    "training_preflight_authorized_next": False,
                    "replay_execution_authorized_next": False,
                    "fixed_dp_candidate_generation_authorized_next": False,
                    "dp_modification_authorized": False,
                },
                "remediation_plan": {
                    "required_static_contracts": required,
                    "blocked_by_this_plan": blocked,
                    "forbidden_reuse": {
                        "reuse_current_failed_evaluation_output_dir": True,
                        "reuse_any_training_manifest_selection_log_as_eval": True,
                        "reuse_recovered_prior_c92_registry_records_as_eval": True,
                        "reuse_eval_route_seed_npc_spawn_tl_static_shadow_signature_in_training": True,
                    },
                },
            }
        ),
    )


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    return _write(
        path,
        "\n".join(
            [
                f"current_v13_status={LATEST_STATUS}",
                f"next_work_target={target}",
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
    target: str = AUTHORIZED_CURRENT_WORK,
    missing_contract: str | None = None,
    leak_action: str | None = None,
) -> dict:
    return build_report(
        nonoverlap_failure_remediation_plan_json=_plan(
            tmp_path / "plan.json",
            missing_contract=missing_contract,
            leak_action=leak_action,
        ),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_nonoverlap_failure_remediation_static_contract_accepts_plan(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == PASS_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fresh_evaluation_split_plan_authorized_next"] is True
    assert decision["training_preflight_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert report["analysis"]["score_expression"] == "score_k(w)=a_k^T w"


def test_nonoverlap_failure_remediation_static_contract_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "latest_audit_target_authorizes_static_review" in report["final_decision"][
        "failed_checks"
    ]


def test_nonoverlap_failure_remediation_static_contract_rejects_missing_contract(
    tmp_path: Path,
) -> None:
    report = _report(
        tmp_path,
        missing_contract="recovered_missing_prior_registry_must_be_loaded",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_required_contracts_present" in report["final_decision"][
        "failed_checks"
    ]


def test_nonoverlap_failure_remediation_static_contract_rejects_action_leak(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, leak_action="replay_execution")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_blocked_actions_present" in report["final_decision"]["failed_checks"]


def test_nonoverlap_failure_remediation_static_contract_main_writes_outputs(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path / "plan.json")
    audit = _audit(tmp_path / "audit.md")
    output_json = tmp_path / "review.json"
    output_md = tmp_path / "review.md"

    exit_code = main(
        [
            "--nonoverlap_failure_remediation_plan_json",
            str(plan),
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
    ] == PASS_STATUS
    assert PASS_STATUS in output_md.read_text(encoding="utf-8")
