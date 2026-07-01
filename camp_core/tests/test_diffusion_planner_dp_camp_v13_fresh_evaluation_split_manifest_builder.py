from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.integrations.build_diffusion_planner_dp_camp_v13_fresh_evaluation_split_manifest import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    FIXED_DP_HEAD,
    FRESH_SCOPE_MANIFEST_SCHEMA_VERSION,
    NONOVERLAP_REGISTRY_REPORT_SCHEMA_VERSION,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_BEHAVIOR,
    SCHEMA_VERSION,
    SHA256SUMS_NAME,
    SOURCE_REGISTRY_SCHEMA_VERSION,
    SOURCE_REVIEW_SCHEMA_VERSION,
    SOURCE_REVIEW_STATUS,
    TARGET_RECORDS,
    TARGET_SELECTION_LOGS,
    TRAINING_RECORDS,
    TRAINING_SELECTION_LOGS,
    TRAINING_SELECTION_MANIFEST_SCHEMA_VERSION,
    build_manifest_report,
    main,
)


CAMP_HEAD = "d59d7385cf00ca75afa32eb646cd3f8d8da3d0db"


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _static_review(path: Path, *, mutation: Any | None = None) -> Path:
    payload = {
        "schema_version": SOURCE_REVIEW_SCHEMA_VERSION,
        "final_decision": {
            "status": SOURCE_REVIEW_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "fresh_evaluation_split_implementation_authorized_next": True,
            "implementation_authorized_next": True,
            "data_preparation_authorized_next": False,
            "training_preflight_authorized_next": False,
            "training_execution_authorized_next": False,
            "replay_execution_authorized_next": False,
            "fixed_dp_candidate_generation_authorized_next": False,
            "candidate_generation_by_camp_authorized": False,
            "trajectory_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
        "static_contract_review": {
            "future_builder_script": (
                "scripts/integrations/build_diffusion_planner_dp_camp_v13_"
                "fresh_evaluation_split_manifest.py"
            ),
            "future_builder_test": (
                "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
                "fresh_evaluation_split_manifest_builder.py"
            ),
            "required_behavior": list(REQUIRED_BEHAVIOR),
            "future_scope_contract": {
                "selection_log_count": TARGET_SELECTION_LOGS,
                "record_count": TARGET_RECORDS,
                "candidate_count": 8,
                "atom_count": 14,
                "routes_minimum": 4,
                "seeds_minimum": 2,
                "route_traffic_light_buckets_minimum": 8,
            },
            "math_boundary": {
                "candidate_operation": "fixed DP candidate reranking only",
                "score_expression": "score_k(w)=a_k^T w",
                "nonnegative_simplex_weights_only": True,
            },
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _training_manifest(path: Path, *, mutation: Any | None = None) -> Path:
    entries = []
    for idx in range(TRAINING_SELECTION_LOGS):
        source = "evaluation" if idx < TARGET_SELECTION_LOGS else "prior"
        route = ["sample_normal", "sample_tl", "nishi_lane_change", "nishi_release"][idx % 4]
        seed = 2100 + (idx % 8)
        rel = f"{route}/seed_{seed}/npc_0/spawn_0p3/tl_off/static_shadow/camp_selection_log.json"
        entries.append(
            {
                "path": f"/tmp/fixed_training/{rel}",
                "relative_path": rel,
                "sha256": f"{idx:064x}"[-64:],
                "records": 100,
                "source": source,
            }
        )
    payload = {
        "schema_version": TRAINING_SELECTION_MANIFEST_SCHEMA_VERSION,
        "selection_log_count": TRAINING_SELECTION_LOGS,
        "records_total": TRAINING_RECORDS,
        "entries": entries,
        "candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _touch_json(path: Path) -> Path:
    return _write_json(path, {"ok": True})


def _registry(path: Path, *, mutation: Any | None = None) -> Path:
    registry_dir = path.parent
    candidate = _touch_json(registry_dir / "candidate_tensor_hash_registry.json")
    path_sig = _touch_json(registry_dir / "path_signature_registry.json")
    record = _touch_json(registry_dir / "record_identity_hash_registry.json")
    split = _touch_json(registry_dir / "split_manifest.json")
    training = _touch_json(registry_dir / "training_manifest.json")
    payload = {
        "schema_version": SOURCE_REGISTRY_SCHEMA_VERSION,
        "candidate_tensor_hash_registry_json": str(candidate),
        "path_signature_registry_json": str(path_sig),
        "record_identity_hash_registry_json": str(record),
        "split_manifest_json": str(split),
        "training_manifest_json": str(training),
        "training_manifest_log_count": TRAINING_SELECTION_LOGS,
        "training_existing_log_count": 320,
        "training_missing_log_count": 96,
        "training_candidate_hash_count": 41600,
        "evaluation_candidate_hash_count": 3200,
        "recovered_candidate_hash_count": 3200,
        "recovered_path_signature_count": 3200,
        "recovered_record_identity_count": 3200,
        "candidate_hash_intersection_count": 2140,
        "path_signature_intersection_count": 32,
        "record_identity_intersection_count": 3200,
        "candidate_tensor_eval_hashes_in_previous_count": 3200,
        "candidate_tensor_eval_hashes_in_previous_rate": 1.0,
        "training_formal_seed_count": 0,
        "evaluation_formal_seed_count": 0,
        "training_missing_log_sample": [
            "/tmp/fixed_eval/sample_normal/seed_2000/tl_off/static_shadow/camp_selection_log.json"
        ],
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(path, payload)


def _audit(path: Path, *, current_work: str = AUTHORIZED_CURRENT_WORK) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "current_v13_status=static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_implementation_static_contract_review_passed",
                f"next_work_target={current_work}",
                "data_preparation_authorized_next=False",
                "training_preflight_authorized_next=False",
                "training_execution_authorized_by_current_boundary=False",
                "runtime_shadow_selector_execution_authorized=False",
                "replay_execution_authorized_by_current_boundary=False",
                "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
                "candidate_generation_by_camp_authorized_by_current_boundary=False",
                "trajectory_generation_by_camp_authorized_by_current_boundary=False",
                "trajectory_modification_by_camp_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "formal_seed_11_12_13_execution_authorized=False",
                "reference_blend_authorized=False",
                "guidance_authorized=False",
                "postprocess_or_postselection_authorized=False",
                "closed_loop_outcome_authorized=False",
                "online_selector_change_authorized=False",
                "executed_trajectory_change_authorized=False",
                "selector_promotion_authorized=False",
                "atom_promotion_authorized=False",
                "deployment_authorized=False",
                "deployable_checkpoint_claim_authorized=False",
                "safety_benefit_claim_authorized=False",
                "camp_over_dp_top1_claim_authorized=False",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _build(
    tmp_path: Path,
    *,
    enabled: bool = True,
    current_work: str = AUTHORIZED_CURRENT_WORK,
    review_mutation: Any | None = None,
    training_mutation: Any | None = None,
    recovered_mutation: Any | None = None,
    rejected_mutation: Any | None = None,
    current_dp_head: str = FIXED_DP_HEAD,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    review = _static_review(tmp_path / "static_review.json", mutation=review_mutation)
    training = _training_manifest(tmp_path / "training_selection_manifest.json", mutation=training_mutation)
    recovered = _registry(tmp_path / "recovered" / "registry_manifest.json", mutation=recovered_mutation)
    rejected = _registry(tmp_path / "rejected" / "registry_manifest.json", mutation=rejected_mutation)
    output_root = output_dir or (tmp_path / "out")
    return build_manifest_report(
        implementation_static_contract_review_json=review,
        expected_static_contract_review_sha256=_sha256(review),
        training_selection_manifest_json=training,
        recovered_prior_registry_manifest_json=recovered,
        rejected_evaluation_source_registry_manifest_json=rejected,
        v13_audit_md=_audit(tmp_path / "audit.md", current_work=current_work),
        output_dir=output_root,
        output_json=output_root / "fresh_evaluation_split_manifest_builder_report.json",
        output_md=output_root / "fresh_evaluation_split_manifest_builder_report.md",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=current_dp_head,
        enabled=enabled,
    )


def test_manifest_builder_is_default_off_and_has_no_side_effects(tmp_path: Path) -> None:
    output_root = tmp_path / "out"
    report = build_manifest_report(
        implementation_static_contract_review_json=tmp_path / "missing_review.json",
        expected_static_contract_review_sha256="0" * 64,
        training_selection_manifest_json=tmp_path / "missing_training.json",
        recovered_prior_registry_manifest_json=tmp_path / "missing_recovered.json",
        rejected_evaluation_source_registry_manifest_json=tmp_path / "missing_rejected.json",
        v13_audit_md=tmp_path / "missing_audit.md",
        output_dir=output_root,
        output_json=output_root / "report.json",
        output_md=output_root / "report.md",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["checks"] == []
    assert not output_root.exists()


def test_manifest_builder_writes_manifest_only_outputs_when_enabled(tmp_path: Path) -> None:
    output_root = tmp_path / "out"
    report = _build(tmp_path, output_dir=output_root)

    assert report["schema_version"] == SCHEMA_VERSION
    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["manifest_files_written"] is True
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["data_preparation_authorized_next"] is False
    assert report["final_decision"]["fixed_dp_candidate_generation_authorized_next"] is False
    assert report["final_decision"]["training_execution_authorized_next"] is False
    assert report["final_decision"]["replay_execution_authorized_next"] is False
    assert report["final_decision"]["dp_modification_authorized"] is False
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False
    assert report["final_decision"]["fresh_evaluation_split_members_selected"] is False

    scope = json.loads(
        (output_root / "fresh_evaluation_split_scope_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    registry = json.loads(
        (output_root / "fresh_evaluation_split_nonoverlap_registry_report.json").read_text(
            encoding="utf-8"
        )
    )
    runbook = (output_root / "run_fresh_evaluation_split_preflight.sh").read_text(
        encoding="utf-8"
    )

    assert scope["schema_version"] == FRESH_SCOPE_MANIFEST_SCHEMA_VERSION
    assert scope["target_selection_log_count"] == TARGET_SELECTION_LOGS
    assert scope["target_record_count"] == TARGET_RECORDS
    assert scope["fresh_split_members_selected_by_this_builder"] is False
    assert scope["executions_requested_by_this_manifest"] == {
        "data_preparation": False,
        "deployment": False,
        "dp_modification": False,
        "fixed_dp_candidate_generation": False,
        "replay": False,
        "selector_or_atom_promotion": False,
        "training": False,
    }
    assert registry["schema_version"] == NONOVERLAP_REGISTRY_REPORT_SCHEMA_VERSION
    assert registry["zero_intersection_proof_executed_by_this_builder"] is False
    assert registry["future_zero_intersection_preflight_required"] is True
    assert registry["nonoverlap_requirements_for_future_fresh_split"] == {
        "candidate_tensor_hash_intersection_count": 0,
        "path_signature_intersection_count": 0,
        "record_identity_intersection_count": 0,
        "split_manifest_root_intersection_count": 0,
    }
    assert "no DP execution" in runbook


def test_manifest_builder_main_writes_report_and_sha256sums(tmp_path: Path) -> None:
    review = _static_review(tmp_path / "static_review.json")
    training = _training_manifest(tmp_path / "training_selection_manifest.json")
    recovered = _registry(tmp_path / "recovered" / "registry_manifest.json")
    rejected = _registry(tmp_path / "rejected" / "registry_manifest.json")
    output_root = tmp_path / "out"
    output_json = output_root / "fresh_evaluation_split_manifest_builder_report.json"
    output_md = output_root / "fresh_evaluation_split_manifest_builder_report.md"

    exit_code = main(
        [
            "--implementation_static_contract_review_json",
            str(review),
            "--expected_static_contract_review_sha256",
            _sha256(review),
            "--training_selection_manifest_json",
            str(training),
            "--recovered_prior_registry_manifest_json",
            str(recovered),
            "--rejected_evaluation_source_registry_manifest_json",
            str(rejected),
            "--v13_audit_md",
            str(_audit(tmp_path / "audit.md")),
            "--output_dir",
            str(output_root),
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--enable_v13_fresh_evaluation_split_manifest_builder",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert (output_root / SHA256SUMS_NAME).is_file()
    sha_text = (output_root / SHA256SUMS_NAME).read_text(encoding="utf-8")
    assert "fresh_evaluation_split_scope_manifest.json" in sha_text
    assert "fresh_evaluation_split_manifest_builder_report.json" not in sha_text
    assert "manifest-only" in output_md.read_text(encoding="utf-8")


def test_manifest_builder_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _build(tmp_path, current_work="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "latest_audit_target_authorizes_builder" in report["final_decision"]["failed_checks"]


def test_manifest_builder_rejects_source_action_leak(tmp_path: Path) -> None:
    def authorize_replay(payload: dict[str, Any]) -> None:
        payload["final_decision"]["replay_execution_authorized_next"] = True

    report = _build(tmp_path, review_mutation=authorize_replay)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_review_blocks_forbidden_actions" in report["final_decision"]["failed_checks"]


def test_manifest_builder_rejects_missing_required_behavior(tmp_path: Path) -> None:
    def drop_behavior(payload: dict[str, Any]) -> None:
        payload["static_contract_review"]["required_behavior"] = list(REQUIRED_BEHAVIOR[:-1])

    report = _build(tmp_path, review_mutation=drop_behavior)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_review_required_behavior_present" in report["final_decision"]["failed_checks"]


def test_manifest_builder_accepts_static_review_without_optional_scope_minima(
    tmp_path: Path,
) -> None:
    def drop_optional_minima(payload: dict[str, Any]) -> None:
        scope = payload["static_contract_review"]["future_scope_contract"]
        scope.pop("routes_minimum")
        scope.pop("seeds_minimum")
        scope.pop("route_traffic_light_buckets_minimum")

    report = _build(tmp_path, review_mutation=drop_optional_minima)

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["failed_checks"] == []


def test_manifest_builder_rejects_empty_recovered_registry(tmp_path: Path) -> None:
    def empty_recovered(payload: dict[str, Any]) -> None:
        payload["recovered_candidate_hash_count"] = 0

    report = _build(tmp_path, recovered_mutation=empty_recovered)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "recovered_prior_registry_recovered_candidate_hashes_nonempty"
        in report["final_decision"]["failed_checks"]
    )


def test_manifest_builder_rejects_missing_registry_file(tmp_path: Path) -> None:
    def missing_file(payload: dict[str, Any]) -> None:
        payload["candidate_tensor_hash_registry_json"] = str(
            tmp_path / "recovered" / "missing_candidate_registry.json"
        )

    report = _build(tmp_path, recovered_mutation=missing_file)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "recovered_prior_registry_referenced_files_nonempty"
        in report["final_decision"]["failed_checks"]
    )


def test_manifest_builder_rejects_formal_seed_in_training_manifest(tmp_path: Path) -> None:
    def add_formal_seed(payload: dict[str, Any]) -> None:
        payload["entries"][0]["relative_path"] = (
            "sample_normal/seed_11/tl_off/static_shadow/camp_selection_log.json"
        )

    report = _build(tmp_path, training_mutation=add_formal_seed)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "training_manifest_no_formal_seeds" in report["final_decision"]["failed_checks"]


def test_manifest_builder_rejects_dp_head_drift(tmp_path: Path) -> None:
    report = _build(tmp_path, current_dp_head="0" * 40)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_manifest_builder_rejects_output_path_outside_output_dir(tmp_path: Path) -> None:
    review = _static_review(tmp_path / "static_review.json")
    training = _training_manifest(tmp_path / "training_selection_manifest.json")
    recovered = _registry(tmp_path / "recovered" / "registry_manifest.json")
    rejected = _registry(tmp_path / "rejected" / "registry_manifest.json")
    output_root = tmp_path / "out"
    report = build_manifest_report(
        implementation_static_contract_review_json=review,
        expected_static_contract_review_sha256=_sha256(review),
        training_selection_manifest_json=training,
        recovered_prior_registry_manifest_json=recovered,
        rejected_evaluation_source_registry_manifest_json=rejected,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        output_dir=output_root,
        output_json=tmp_path / "outside_report.json",
        output_md=output_root / "report.md",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "output_json_under_output_dir" in report["final_decision"]["failed_checks"]
