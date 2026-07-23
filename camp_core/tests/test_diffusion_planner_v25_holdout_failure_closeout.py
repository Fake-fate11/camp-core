from __future__ import annotations

import copy
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
    freeze_experiment_protocol,
    freeze_holdout_identity,
)
from camp_core.integrations.diffusion_planner_v25_holdout_failure_closeout import (
    freeze_consumed_holdout_failure_closeout,
    independent_failure_review,
    validate_consumed_holdout_failure_closeout,
)
from camp_core.integrations import diffusion_planner_v25_holdout_protocol as protocol


def _identity() -> dict:
    return freeze_holdout_identity(
        split="fresh_b2",
        scenario_manifest_sha256="1" * 64,
        map_suite_payload_sha256="2" * 64,
        route_census_sha256="3" * 64,
        corridor_census_sha256="4" * 64,
        semantic_census_sha256="5" * 64,
        execution_plan_sha256="6" * 64,
        seeds=[25401, 25402, 25403, 25404, 25405],
        arm_order_commit_sha256="7" * 64,
        paired_unit_count=500,
        arm_run_count=1500,
        tick_capacity=96_000,
    )


def _protocol() -> dict:
    return freeze_experiment_protocol(
        model_registry_sha256="1" * 64,
        training_scale_sha256="2" * 64,
        context_scaler_sha256="3" * 64,
        atom_contract_sha256="4" * 64,
        threshold_contract_sha256="5" * 64,
        noninferiority_contract_sha256="6" * 64,
        multiplicity_contract_sha256="7" * 64,
        claim_contract_sha256="8" * 64,
        failure_contract_sha256="9" * 64,
        candidate0_semantics=(
            "action_equivalent_operational_default_first_default_output_alias"
        ),
        same_forward_contract="forward_execution_id_plus_input_model_action_digest",
        latency_contract=(
            "online_operational_plus_supplementary_evidence_plus_runtime_total_v1"
        ),
        terminal_truth_table="exclusive_scientific_terminal_or_artifact_fatal_v1",
    )


def _binding(name: str, digit: str) -> dict:
    return {
        "path": f"/root/autodl-tmp/{name}",
        "root_sha256": digit * 64,
    }


def test_b2_consumed_failure_is_tombstoned_without_outcome_use() -> None:
    closeout = freeze_consumed_holdout_failure_closeout(
        benchmark="fresh_b2",
        holdout_identity=_identity(),
        experiment_protocol=_protocol(),
        reservation_commitment_sha256="a" * 64,
        controller_decision=_binding("controller", "1"),
        opening_release=_binding("release", "2"),
        consumed_marker=_binding("marker", "3"),
        failure_artifact=_binding("failure", "4"),
        attempted_unit_ordinal=0,
        attempted_arm="candidate0",
        raw_run_count=1,
        complete_paired_row_count=0,
    )
    assert validate_consumed_holdout_failure_closeout(closeout) == closeout
    review = independent_failure_review(closeout, reviewed_root_sha256="5" * 64)
    assert review["terminal_state"] == "terminal_failure"
    assert review["second_opening_allowed"] is False
    assert review["pooling_into_future_experiment_allowed"] is False

    for mutation in (
        lambda row: row.update(raw_outcome_values_inspected=True),
        lambda row: row.update(complete_paired_row_count=1),
        lambda row: row.update(new_nonce_allowed=True),
        lambda row: row.update(extra=True),
    ):
        changed = copy.deepcopy(closeout)
        mutation(changed)
        with pytest.raises(ValueError):
            validate_consumed_holdout_failure_closeout(changed)


def test_accepted_b2_review_uses_exact_live_outcome_blind_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    preopen = tmp_path / "preopen"
    review = tmp_path / "review"
    preopen.mkdir()
    review.mkdir()
    authority = {
        "status": "passed_outcome_blind_fresh_b2_preopen_authority",
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    (preopen / "preopen_authority.json").write_bytes(
        protocol.canonical_json_bytes(authority)
    )
    report = {
        "status": (
            "passed_independent_outcome_blind_fresh_b2_preopen_review"
        ),
        "reviewed_root_sha256": "1" * 64,
    }
    (review / "report.json").write_bytes(
        protocol.canonical_json_bytes(report)
    )
    monkeypatch.setattr(
        protocol, "_verify_successful_artifact", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        protocol, "validate_preopen_authority", lambda value: value
    )
    loaded, loaded_review = protocol.load_accepted_preopen_authority(
        preopen_artifact=preopen,
        preopen_root_sha256="1" * 64,
        preopen_review_artifact=review,
        preopen_review_root_sha256="2" * 64,
    )
    assert loaded == authority
    assert loaded_review == report

    report["status"] = "passed_independent_fresh_b2_preopen_review"
    (review / "report.json").write_bytes(
        protocol.canonical_json_bytes(report)
    )
    with pytest.raises(ValueError, match="chain drifted"):
        protocol.load_accepted_preopen_authority(
            preopen_artifact=preopen,
            preopen_root_sha256="1" * 64,
            preopen_review_artifact=review,
            preopen_review_root_sha256="2" * 64,
        )
