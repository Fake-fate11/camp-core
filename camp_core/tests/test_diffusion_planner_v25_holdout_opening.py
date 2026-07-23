from __future__ import annotations

import copy
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
    freeze_experiment_protocol,
    freeze_holdout_identity,
    reserve_holdout_identity,
    validate_tombstone,
)
from camp_core.integrations.diffusion_planner_v25_holdout_opening import (
    freeze_holdout_controller_decision,
    freeze_holdout_opening_release,
    freeze_opening_commitment,
    validate_holdout_controller_decision,
    validate_holdout_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_holdout_opening_rc import (
    freeze_scientific_exposure_receipt,
    freeze_production_rc_controller_decision,
    freeze_production_rc_opening_release,
    validate_production_rc_controller_decision,
    validate_production_rc_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_holdout_state import (
    operational_attempt_path,
    operational_identity_path,
    reserve_operational_attempt,
    seal_operational_release,
    scientific_identity_path,
    start_scientific_exposure,
)
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (
    TRACKED_AUTHORITY_FILES,
)


def _identity() -> dict:
    return freeze_holdout_identity(
        split="fresh_b3",
        scenario_manifest_sha256="1" * 64,
        map_suite_payload_sha256="2" * 64,
        route_census_sha256="3" * 64,
        corridor_census_sha256="4" * 64,
        semantic_census_sha256="5" * 64,
        execution_plan_sha256="6" * 64,
        seeds=[25501, 25502, 25503, 25504, 25505],
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


def _binding(name: str, sha: str) -> dict:
    return {
        "path": f"/root/autodl-tmp/{name}",
        "root_sha256": sha * 64,
    }


def _release(identity: dict, protocol: dict, cas_path: str) -> dict:
    return freeze_holdout_opening_release(
        implementation_source_head="a" * 40,
        pointer_head_at_release="b" * 40,
        critical_implementation_manifest_sha256="c" * 64,
        controller_decision_root_sha256="d" * 64,
        preopen_authority=_binding("preopen", "1"),
        preopen_review=_binding("preopen-review", "2"),
        production_composition_preflight=_binding("preflight", "3"),
        production_composition_preflight_review=_binding(
            "preflight-review", "4"
        ),
        b2_tombstone=_binding("b2-tombstone", "5"),
        b2_failure_review=_binding("b2-failure-review", "6"),
        holdout_identity=identity,
        experiment_protocol=protocol,
        run_nonce="e" * 64,
        authorized_output_dir="/root/autodl-tmp/fresh_b3_exact_output",
        cas_tombstone_path=cas_path,
    )


def test_controller_decision_is_exact_and_does_not_reserve_cas() -> None:
    identity = _identity()
    protocol = _protocol()
    cas_path = (
        "/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas/"
        f"{identity['holdout_identity_sha256']}.json"
    )
    controller = freeze_holdout_controller_decision(
        implementation_source_head="a" * 40,
        pointer_head_at_release="b" * 40,
        critical_implementation_manifest_sha256="c" * 64,
        preopen_authority=_binding("preopen", "1"),
        preopen_review=_binding("preopen-review", "2"),
        production_composition_preflight=_binding("preflight", "3"),
        production_composition_preflight_review=_binding(
            "preflight-review", "4"
        ),
        b2_tombstone=_binding("b2-tombstone", "5"),
        b2_failure_review=_binding("b2-failure-review", "6"),
        holdout_identity=identity,
        experiment_protocol=protocol,
        run_nonce="e" * 64,
        authorized_output_dir="/root/autodl-tmp/fresh_b3_exact_output",
        cas_tombstone_path=cas_path,
    )
    assert validate_holdout_controller_decision(controller) == controller
    assert controller["holdout_open_authorized"] is True
    assert controller["fresh_outcome_consumed"] is False
    changed = copy.deepcopy(controller)
    changed["full_r_authorized"] = True
    with pytest.raises(ValueError, match="exact value"):
        validate_holdout_controller_decision(changed)


def test_generic_holdout_production_chain_is_frozen_in_critical_manifest() -> None:
    required = {
        (
            "camp_core/camp_core/integrations/"
            "diffusion_planner_v25_holdout_lifecycle_preflight.py"
        ),
        "scripts/integrations/create_diffusion_planner_v25_holdout_opening.py",
        "scripts/integrations/run_diffusion_planner_v25_holdout_execution.py",
        "scripts/integrations/review_diffusion_planner_v25_holdout_execution.py",
        "scripts/integrations/evaluate_diffusion_planner_v25_holdout.py",
        "scripts/integrations/review_diffusion_planner_v25_holdout_evaluation.py",
    }
    assert required.issubset(set(TRACKED_AUTHORITY_FILES))


def test_release_requires_preflight_and_one_identity_commitment(tmp_path: Path) -> None:
    identity = _identity()
    protocol = _protocol()
    cas_path = (
        "/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas/"
        f"{identity['holdout_identity_sha256']}.json"
    )
    release = _release(identity, protocol, cas_path)
    assert validate_holdout_opening_release(release) == release
    expected_commitment = freeze_opening_commitment(
        holdout_identity_sha256=identity["holdout_identity_sha256"],
        experiment_protocol_sha256=protocol["experiment_protocol_sha256"],
        controller_decision_root_sha256="d" * 64,
        preopen_root_sha256="1" * 64,
        preflight_root_sha256="3" * 64,
        run_nonce="e" * 64,
        authorized_output_dir="/root/autodl-tmp/fresh_b3_exact_output",
    )
    assert release["reservation_commitment_sha256"] == expected_commitment
    for field, replacement in (
        ("run_nonce", "f" * 64),
        ("authorized_output_dir", "/root/autodl-tmp/alternate"),
    ):
        changed = copy.deepcopy(release)
        changed[field] = replacement
        with pytest.raises(ValueError, match="exact value"):
            validate_holdout_opening_release(changed)


def test_production_rc_binds_an_independent_nonfresh_canary_cas(
    tmp_path: Path,
) -> None:
    identity = _identity()
    protocol = _protocol()
    cas_root = tmp_path / "nonfresh-canary-cas"
    common = {
        "implementation_source_head": "a" * 40,
        "pointer_head_at_release": "b" * 40,
        "critical_implementation_manifest_sha256": "c" * 64,
        "preopen_authority": _binding("preopen", "1"),
        "preopen_review": _binding("preopen-review", "2"),
        "production_composition_preflight": _binding("preflight", "3"),
        "production_composition_preflight_review": _binding(
            "preflight-review", "4"
        ),
        "b2_tombstone": _binding("b2-tombstone", "5"),
        "b2_failure_review": _binding("b2-failure-review", "6"),
        "holdout_identity": identity,
        "experiment_protocol": protocol,
        "run_nonce": "e" * 64,
        "authorized_output_dir": "/root/autodl-tmp/nonfresh-canary-output",
        "cas_root": cas_root,
    }
    controller = freeze_production_rc_controller_decision(**common)
    assert validate_production_rc_controller_decision(controller) == controller
    assert controller["scientific_ledger_path"] == str(
        scientific_identity_path(
            cas_root, identity["holdout_identity_sha256"]
        )
    )
    assert controller["operational_attempt_path"] == str(
        operational_attempt_path(cas_root, "e" * 64)
    )
    assert controller["operational_identity_reservation_path"] == str(
        operational_identity_path(
            cas_root, identity["holdout_identity_sha256"]
        )
    )

    release = freeze_production_rc_opening_release(
        **common,
        controller_decision_root_sha256="d" * 64,
    )
    assert validate_production_rc_opening_release(release) == release
    assert release["scientific_ledger_path"] == controller[
        "scientific_ledger_path"
    ]


def test_native_runner_accepts_production_rc_exposure_receipt(
    tmp_path: Path,
) -> None:
    identity = _identity()
    protocol = _protocol()
    cas_root = tmp_path / "native-production-rc-cas"
    release_root = "f" * 64
    controller_root = "d" * 64
    common = {
        "implementation_source_head": "a" * 40,
        "pointer_head_at_release": "b" * 40,
        "critical_implementation_manifest_sha256": "c" * 64,
        "preopen_authority": _binding("preopen", "1"),
        "preopen_review": _binding("preopen-review", "2"),
        "production_composition_preflight": _binding("preflight", "3"),
        "production_composition_preflight_review": _binding(
            "preflight-review", "4"
        ),
        "b2_tombstone": _binding("b2-tombstone", "5"),
        "b2_failure_review": _binding("b2-failure-review", "6"),
        "holdout_identity": identity,
        "experiment_protocol": protocol,
        "run_nonce": "e" * 64,
        "authorized_output_dir": "/root/autodl-tmp/nonfresh-native-output",
        "cas_root": cas_root,
    }
    release = freeze_production_rc_opening_release(
        **common,
        controller_decision_root_sha256=controller_root,
    )
    operational_path = reserve_operational_attempt(
        cas_root,
        holdout_identity_sha256=identity["holdout_identity_sha256"],
        experiment_protocol_sha256=protocol["experiment_protocol_sha256"],
        run_nonce="e" * 64,
        authorized_output_dir="/root/autodl-tmp/nonfresh-native-output",
        controller_root_sha256=controller_root,
    )
    seal_operational_release(
        operational_path,
        opening_release_root_sha256=release_root,
    )
    operational, scientific = start_scientific_exposure(
        cas_root,
        operational_attempt=operational_path,
        first_unit_ordinal=0,
        first_arm="candidate0_operational_default",
    )
    exposure = freeze_scientific_exposure_receipt(
        opening_release=release,
        opening_release_root_sha256=release_root,
        operational_attempt=operational,
        scientific_ledger=scientific,
    )
    from scripts.integrations import (
        run_diffusion_planner_dp_camp_v21_native as native,
    )

    result = native._validate_holdout_opening_authority(
        {
            "holdout_authority": {
                "holdout_identity_sha256": identity[
                    "holdout_identity_sha256"
                ],
                "experiment_protocol_sha256": protocol[
                    "experiment_protocol_sha256"
                ],
                "split": "fresh_b3",
            },
            "runtime_selector_authority": {
                "model_registry_sha256": protocol[
                    "model_registry_sha256"
                ],
                "training_scale_sha256": protocol[
                    "training_scale_sha256"
                ],
                "context_scaler_sha256": protocol[
                    "context_scaler_sha256"
                ],
            },
        },
        {
            "opening_release": release,
            "opening_release_root_sha256": release_root,
            "opening_consumption": exposure,
        },
    )
    assert result["opening_release"] == release
    assert result["opening_consumption"] == exposure


def test_pre_marker_failure_is_unconsumed_and_post_marker_is_permanent(
    tmp_path: Path,
) -> None:
    identity = _identity()
    protocol = _protocol()
    expected_remote = (
        "/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas/"
        f"{identity['holdout_identity_sha256']}.json"
    )
    release = _release(identity, protocol, expected_remote)
    local_cas = tmp_path / "cas"
    path = reserve_holdout_identity(
        local_cas,
        holdout_identity=identity,
        experiment_protocol=protocol,
        reservation_commitment_sha256=release[
            "reservation_commitment_sha256"
        ],
    )
    # A pre-marker exception leaves the persistent reservation unconsumed.
    reserved = validate_tombstone(
        __import__("json").loads(path.read_text(encoding="utf-8"))
    )
    assert reserved["state"] == "reserved"

    # The production release requires the canonical AutoDL path.  The unit
    # fixture exercises the same atomic CAS transition primitive locally.
    from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
        transition_holdout_identity,
    )

    opened = transition_holdout_identity(
        path,
        expected_state="reserved",
        next_state="opened_consumed",
        opening_release_root_sha256="f" * 64,
        marker_sha256="0" * 64,
    )
    assert opened["state"] == "opened_consumed"
    with pytest.raises(FileExistsError):
        transition_holdout_identity(
            path,
            expected_state="reserved",
            next_state="opened_consumed",
            opening_release_root_sha256="1" * 64,
            marker_sha256="2" * 64,
        )
    with pytest.raises(FileExistsError):
        reserve_holdout_identity(
            local_cas,
            holdout_identity=identity,
            experiment_protocol=protocol,
            reservation_commitment_sha256="3" * 64,
        )
