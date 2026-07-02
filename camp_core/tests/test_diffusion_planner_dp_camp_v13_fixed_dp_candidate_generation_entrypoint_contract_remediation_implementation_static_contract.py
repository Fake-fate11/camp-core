from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fixed_dp_candidate_generation_entrypoint_contract_remediation_implementation_static_contract import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    FUTURE_RUNNER_SCRIPT,
    FUTURE_RUNNER_TEST,
    PASS_STATUS,
    PLAN_DECISION_FALSE_FLAGS,
    PLAN_READY_STATUS,
    PLAN_SCHEMA_VERSION,
    REJECT_STATUS,
    REQUIRED_RUNNER_CONTRACT_REQUIREMENTS,
    SCHEMA_VERSION,
    ZERO_OVERLAP_KEYS,
    build_report,
    main,
)


CAMP_HEAD = "1bc89559d1ebf1d2a168e11d4674759c281977d7"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_fixed_dp_"
    "candidate_generation_entrypoint_contract_remediation_implementation_plan_ready"
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


def _plan(path: Path, *, mutation: Any | None = None) -> Path:
    decision = {
        "status": PLAN_READY_STATUS,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "entrypoint_contract_remediation_implementation_plan_ready": True,
        "entrypoint_contract_remediation_implementation_static_contract_review_authorized_next": True,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }
    for flag in PLAN_DECISION_FALSE_FLAGS:
        decision[flag] = False
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "entrypoint_contract_remediation_implementation_plan": {
            "implementation_performed_by_this_gate": False,
            "future_runner_script": FUTURE_RUNNER_SCRIPT,
            "future_runner_test": FUTURE_RUNNER_TEST,
            "runner_owner_repo": "CAMP",
            "missing_dp_repo_entrypoint_will_not_be_created": True,
            "dp_repo_modification_allowed": False,
            "dp_config_weight_checkpoint_change_allowed": False,
            "candidate_source": "fixed Diffusion Planner candidate tensor only",
            "required_dp_head": FIXED_DP_HEAD,
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
            "runner_contract_requirements": list(REQUIRED_RUNNER_CONTRACT_REQUIREMENTS),
            "future_static_review_requirements": [
                "reject_if_runner_path_is_in_diffusion_planner_repo",
                "reject_if_runner_can_modify_dp_code_config_weights_or_checkpoints",
                "reject_if_runner_can_generate_repair_rewrite_or_blend_trajectories_with_camp",
                "reject_if_runner_omits_candidate_tensor_hash_registry",
                "reject_if_runner_omits_path_signature_registry",
                "reject_if_runner_omits_record_identity_registry",
                "reject_if_runner_omits_split_manifest_root_registry",
                "reject_if_runner_allows_full36_or_formal_seeds_11_12_13",
                "reject_if_training_data_preparation_promotion_or_deployment_is_authorized",
                "reject_if_score_is_not_affine_or_weights_are_not_nonnegative_simplex",
            ],
        },
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _plan_script(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "FUTURE_RUNNER_SCRIPT",
                "entrypoint_contract_remediation_implementation_static_contract_review_authorized_next",
                "entrypoint_contract_remediation_implementation_authorized_next",
                "fixed_dp_candidate_generation_execution_authorized_next",
                "candidate_generation_by_camp_authorized",
                "",
            ]
        ),
    )


def _plan_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "AUTHORIZED_NEXT_WORK",
                "entrypoint_contract_remediation_implementation_static_contract_review_authorized_next",
                "entrypoint_contract_remediation_implementation_authorized_next",
                "fixed_dp_candidate_generation_execution_authorized_next",
                "candidate_generation_by_camp_authorized",
                "",
            ]
        ),
    )


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "entrypoint_contract_remediation_implementation_static_contract_review_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _report(
    tmp_path: Path,
    *,
    target: str = AUTHORIZED_CURRENT_WORK,
    mutation: Any | None = None,
) -> dict[str, Any]:
    return build_report(
        implementation_plan_json=_plan(tmp_path / "plan.json", mutation=mutation),
        implementation_plan_artifact_dir=tmp_path,
        implementation_plan_script=_plan_script(tmp_path / "plan.py"),
        implementation_plan_test=_plan_test(tmp_path / "test_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_entrypoint_remediation_implementation_static_contract_authorizes_implementation_only(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    review = report["implementation_static_contract_review"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == PASS_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert (
        decision["entrypoint_contract_remediation_implementation_static_contract_review_passed"]
        is True
    )
    assert decision["entrypoint_contract_remediation_implementation_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_executed"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert review["runner_contract"]["future_runner_script"] == FUTURE_RUNNER_SCRIPT
    assert review["runner_contract"]["runner_owner_repo"] == "CAMP"
    assert review["zero_overlap_contract"]["record_identity"] is True


def test_entrypoint_remediation_implementation_static_contract_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_target_authorizes_static_review" in report["final_decision"][
        "failed_checks"
    ]


def test_entrypoint_remediation_implementation_static_contract_rejects_action_leak(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["final_decision"]["training_preflight_authorized_next"] = True

    report = _report(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_forbids_training_preflight_authorized_next" in report["final_decision"][
        "failed_checks"
    ]


def test_entrypoint_remediation_implementation_static_contract_rejects_missing_requirement(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["entrypoint_contract_remediation_implementation_plan"][
            "runner_contract_requirements"
        ].remove("runner_requires_fixed_dp_head_before_any_future_execution")

    report = _report(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runner_requirements_complete" in report["final_decision"]["failed_checks"]


def test_entrypoint_remediation_implementation_static_contract_rejects_runner_in_dp_repo(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["entrypoint_contract_remediation_implementation_plan"][
            "future_runner_script"
        ] = "/root/autodl-tmp/Diffusion-Planner/tools/camp_fixed_candidate_generation.py"

    report = _report(tmp_path, mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runner_script_expected" in report["final_decision"]["failed_checks"]
    assert "runner_not_in_dp_repo" in report["final_decision"]["failed_checks"]


def test_entrypoint_remediation_implementation_static_contract_main_writes_outputs(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "review.json"
    output_md = tmp_path / "review.md"

    exit_code = main(
        [
            "--implementation_plan_json",
            str(_plan(tmp_path / "plan.json")),
            "--implementation_plan_artifact_dir",
            str(tmp_path),
            "--implementation_plan_script",
            str(_plan_script(tmp_path / "plan.py")),
            "--implementation_plan_test",
            str(_plan_test(tmp_path / "test_plan.py")),
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

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == PASS_STATUS
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert FUTURE_RUNNER_SCRIPT in output_md.read_text(encoding="utf-8")
