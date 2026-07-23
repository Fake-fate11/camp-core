from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_causal_atoms import (
    FixedDpCandidateGenerationCapabilityFailure,
    validate_fixed_k8_candidate_tensor,
)
from camp_core.integrations.diffusion_planner_v25_fresh_execution import (
    _execute_validated_fresh_units,
    execute_fresh_b2_three_arm_units,
    materialize_source_ineligible_evidence,
    materialize_fixed_dp_failure_evidence,
)
from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (
    RetainedScenarioCapabilityFailure,
    ScenarioCapabilityReason,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
    freeze_experiment_protocol,
    freeze_holdout_identity,
)
from camp_core.integrations.diffusion_planner_v25_holdout_opening import (
    freeze_holdout_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_fresh_opening import (
    freeze_fresh_b2_opening_consumption,
    freeze_fresh_b2_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_fresh_execution_review import (
    _recompute_fixed_dp_failure,
    _review_failure_pair_authority,
    _validate_cross_arm_pair_authority,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_execution import (
    FRESH_PLAN_ARMS,
)


def _opening() -> tuple[dict, str, dict, dict]:
    roots = {
        "calibration_contract_root_sha256": "1" * 64,
        "preopen_qualification_root_sha256": "2" * 64,
        "model_registry_sha256": "3" * 64,
        "training_scale_sha256": "4" * 64,
        "context_scaler_sha256": "5" * 64,
        "scenario_manifest_root_sha256": "6" * 64,
    }
    release = freeze_fresh_b2_opening_release(
        implementation_source_head="a" * 40,
        pointer_head_at_release="b" * 40,
        controller_decision_root_sha256="7" * 64,
        run_nonce="8" * 64,
        authorized_output_dir="/root/autodl-tmp/v25-fresh-test",
        **roots,
    )
    release_root = "9" * 64
    consumption = freeze_fresh_b2_opening_consumption(
        opening_release=release,
        release_root_sha256=release_root,
        marker_sha256="c" * 64,
    )
    return release, release_root, consumption, roots


def _holdout_opening() -> tuple[dict, str, dict, dict]:
    identity = freeze_holdout_identity(
        split="fresh_b3_nonfresh_test",
        scenario_manifest_sha256="1" * 64,
        map_suite_payload_sha256="2" * 64,
        route_census_sha256="3" * 64,
        corridor_census_sha256="4" * 64,
        semantic_census_sha256="5" * 64,
        execution_plan_sha256="6" * 64,
        seeds=[25401],
        arm_order_commit_sha256="7" * 64,
        paired_unit_count=1,
        arm_run_count=3,
        tick_capacity=192,
    )
    protocol = freeze_experiment_protocol(
        model_registry_sha256="8" * 64,
        training_scale_sha256="9" * 64,
        context_scaler_sha256="a" * 64,
        atom_contract_sha256="b" * 64,
        threshold_contract_sha256="c" * 64,
        noninferiority_contract_sha256="d" * 64,
        multiplicity_contract_sha256="e" * 64,
        claim_contract_sha256="f" * 64,
        failure_contract_sha256="0" * 64,
        candidate0_semantics=(
            "action_equivalent_operational_default_first_default_output_alias"
        ),
        same_forward_contract=(
            "forward_execution_id_plus_input_model_action_digest"
        ),
        latency_contract=(
            "online_operational_plus_supplementary_evidence_plus_runtime_total_v1"
        ),
        terminal_truth_table=(
            "exclusive_scientific_terminal_or_artifact_fatal_v1"
        ),
    )
    binding = lambda name, char: {
        "path": f"/root/autodl-tmp/{name}",
        "root_sha256": char * 64,
    }
    cas_path = (
        "/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas/"
        f"{identity['holdout_identity_sha256']}.json"
    )
    release = freeze_holdout_opening_release(
        implementation_source_head="a" * 40,
        pointer_head_at_release="b" * 40,
        critical_implementation_manifest_sha256="c" * 64,
        controller_decision_root_sha256="d" * 64,
        preopen_authority=binding("preopen", "1"),
        preopen_review=binding("preopen-review", "2"),
        production_composition_preflight=binding("preflight", "3"),
        production_composition_preflight_review=binding(
            "preflight-review", "4"
        ),
        b2_tombstone=binding("b2-tombstone", "5"),
        b2_failure_review=binding("b2-failure-review", "6"),
        holdout_identity=identity,
        experiment_protocol=protocol,
        run_nonce="7" * 64,
        authorized_output_dir="/root/autodl-tmp/fresh_b3_nonfresh_test",
        cas_tombstone_path=cas_path,
    )
    release_root = "8" * 64
    consumption = {
        "schema_version": "camp_dp_v25_holdout_opening_consumption_v1",
        "status": "holdout_opened_consumed",
        "opening_release_root_sha256": release_root,
        "holdout_identity_sha256": identity["holdout_identity_sha256"],
        "experiment_protocol_sha256": protocol[
            "experiment_protocol_sha256"
        ],
        "reservation_commitment_sha256": release[
            "reservation_commitment_sha256"
        ],
        "cas_tombstone_path": cas_path,
        "marker_sha256": "9" * 64,
        "consumed_before_outcome_capable_operation": True,
        "second_opening_allowed": False,
        "new_nonce_allowed": False,
        "suffix_allowed": False,
        "outcome_fields_consumed_before_opening": [],
    }
    selector = {
        "preopen_qualification_root_sha256": "1" * 64,
        "model_registry_sha256": "8" * 64,
        "training_scale_sha256": "9" * 64,
        "context_scaler_sha256": "a" * 64,
    }
    return release, release_root, consumption, selector


def _mini_plan() -> dict:
    scenario = "d" * 64
    route = "e" * 64
    unit = "f" * 64
    return {
        "identities": [
            {
                "scenario_identity_sha256": scenario,
                "route_identity_sha256": route,
                "scenario_family": "lead_vehicle_hard_brake",
                "risk_tier": "easy",
                "phase_authority_mode": "observe_same_tick_request",
            }
        ],
        "execution_units": [
            {
                "unit_ordinal": 0,
                "unit_sha256": unit,
                "scenario_identity_sha256": scenario,
                "seed": 25401,
                "ordered_arms": list(FRESH_PLAN_ARMS),
            }
        ],
    }


def _fixed_dp_failure(
    *, bind_fresh: bool = True
) -> FixedDpCandidateGenerationCapabilityFailure:
    candidates = _invalid_candidates()
    candidate0_sha = hashlib.sha256(candidates[0].tobytes()).hexdigest()
    identity = {
        "elementwise_equal": True,
        "max_abs_difference": 0.0,
        "default_output_sha256": candidate0_sha,
        "candidate0_sha256": candidate0_sha,
        "native_ranked_k8": False,
    }
    with pytest.raises(FixedDpCandidateGenerationCapabilityFailure) as caught:
        validate_fixed_k8_candidate_tensor(
            candidates,
            tick_index=5,
            default_output_sha256=candidate0_sha,
            default_candidate0_identity=identity,
        )
    failure = caught.value
    if bind_fresh:
        failure.bind_fresh_failure_authority(
            pair_authority={
                "route_identity_sha256": "e" * 64,
                "semantic_parameter_block_sha256": "f" * 64,
                "native_route_sha256": "1" * 64,
                "logical_map_sha256": "2" * 64,
                "scenario_seed": 25401,
                "spawn_config_sha256": "3" * 64,
                "initial_state_sha256": "4" * 64,
                "initial_input_sha256": "5" * 64,
            },
            signal_phase="green",
        )
    return failure


def _invalid_candidates() -> np.ndarray:
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    candidates[..., 2] = 1.0
    candidates[2, 4, 2:4] = 0.0
    return candidates


def _patch_projection(monkeypatch: pytest.MonkeyPatch) -> None:
    module = __import__(
        "camp_core.integrations.diffusion_planner_v25_fresh_execution",
        fromlist=["unused"],
    )
    monkeypatch.setattr(module, "validate_fresh_b2_manifest_row", lambda row, index: dict(row))
    monkeypatch.setattr(
        module,
        "build_fresh_b2_arm_config",
        lambda **kwargs: {
            "plan_arm": kwargs["plan_arm"],
            "unit": kwargs["execution_unit"]["unit_sha256"],
        },
    )
    monkeypatch.setattr(
        module,
        "build_holdout_arm_config",
        lambda **kwargs: {
            "plan_arm": kwargs["plan_arm"],
            "unit": kwargs["execution_unit"]["unit_sha256"],
            "signal_complete_plan_authority": {
                "route_identity_sha256": "e" * 64,
                "semantic_parameter_block_sha256": "f" * 64,
                "scenario_identity_sha256": "d" * 64,
            },
            "routes": [{"sha256": "1" * 64}],
            "map": {"sha256": "2" * 64},
            "seeds": {"scenario": 25401},
            "spawn_config": {"seed": 25401},
            "signal_complete_runtime": {
                "case": {
                    "scenario_id": "scenario-0",
                    "family": "lead_vehicle_hard_brake",
                    "signal_source_class": "mapped_signal",
                    "phase_authority_mode": "observe_same_tick_request",
                }
            },
        },
    )
    monkeypatch.setattr(
        module,
        "build_candidate0_pool_evidence",
        lambda native: {"native": native["arm"]},
    )
    monkeypatch.setattr(
        module,
        "build_fresh_b2_complete_row",
        lambda **kwargs: {
            "pair_key": kwargs["pair_key"],
            "arm": kwargs["arm"],
            "status": "complete",
        },
    )
    monkeypatch.setattr(
        module,
        "build_fresh_b2_failure_row",
        lambda **kwargs: {
            "pair_key": kwargs["pair_key"],
            "arm": kwargs["arm"],
            "status": kwargs["status"],
        },
    )


def test_three_arm_core_preserves_order_and_retains_only_typed_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_projection(monkeypatch)
    plan = _mini_plan()
    release, release_root, consumption, roots = _opening()
    seen: list[str] = []

    def run_one(config: dict, _run_dir: Path) -> dict:
        seen.append(config["plan_arm"])
        if config["plan_arm"] == "camp_static14d":
            raise _fixed_dp_failure()
        return {"arm": "dp" if "candidate0" in config["plan_arm"] else "camp"}

    report = _execute_validated_fresh_units(
        plan=plan,
        qualification_rows=[{"route_identity_sha256": "e" * 64}],
        probe_template={},
        prepared_runtime_by_scenario={"d" * 64: {}},
        route_asset_by_identity={"e" * 64: {}},
        dp_repo=tmp_path / "dp",
        runtime_selector_authority=roots,
        opening_release=release,
        opening_release_root_sha256=release_root,
        opening_consumption=consumption,
        authorized_output_dir=release["authorized_output_dir"],
        output_dir=tmp_path / "execution",
        run_one=run_one,
        failure_evidence=materialize_fixed_dp_failure_evidence,
    )
    assert seen == list(FRESH_PLAN_ARMS)
    assert report["planned_pair_count"] == 1
    assert report["terminal_arm_run_count"] == 3
    assert report["complete_arm_run_count"] == 2
    assert report["retained_fixed_dp_capability_failure_count"] == 1
    assert report["status"] == "fresh_b2_three_arm_execution_scientifically_ineligible"
    assert len(list((tmp_path / "execution" / "runs").iterdir())) == 3
    static_run = next((tmp_path / "execution" / "runs").glob("*_static14d"))
    evidence = json.loads(
        (static_run / "fixed_dp_failure_receipt.json").read_text(encoding="utf-8")
    )
    rebuilt = _recompute_fixed_dp_failure(static_run, evidence)
    assert rebuilt["reason"] == "invalid_k8_heading_norm_envelope"
    raw_path = static_run / evidence["raw_failure_preimage"]["relative_path"]
    raw = bytearray(raw_path.read_bytes())
    raw[0] ^= 1
    raw_path.write_bytes(raw)
    with pytest.raises(ValueError, match="raw K8 preimage drifted"):
        _recompute_fixed_dp_failure(static_run, evidence)


def test_fixed_dp_failure_evidence_requires_bound_pair_and_signal_authority(
    tmp_path: Path,
) -> None:
    failure = _fixed_dp_failure()
    authority = failure.canonical_fresh_failure_authority()
    result = materialize_fixed_dp_failure_evidence({}, tmp_path, failure)
    assert result["pair_authority"] == authority["pair_authority"]
    assert result["signal_phase"] == "green"
    assert (tmp_path / result["raw_failure_preimage"]["relative_path"]).is_file()

    second = _fixed_dp_failure(bind_fresh=False)
    with pytest.raises(ValueError, match="lacks reset/source authority"):
        materialize_fixed_dp_failure_evidence({}, tmp_path / "missing", second)


def test_generic_holdout_fixed_dp_failure_terminates_whole_unit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_projection(monkeypatch)
    release, release_root, consumption, selector = _holdout_opening()
    seen: list[str] = []

    def run_one(config: dict, _run_dir: Path) -> dict:
        seen.append(config["plan_arm"])
        if config["plan_arm"] == "camp_static14d":
            raise _fixed_dp_failure()
        return {"arm": "dp"}

    report = _execute_validated_fresh_units(
        plan=_mini_plan(),
        qualification_rows=[{"route_identity_sha256": "e" * 64}],
        probe_template={},
        prepared_runtime_by_scenario={"d" * 64: {}},
        route_asset_by_identity={"e" * 64: {}},
        dp_repo=tmp_path / "dp",
        runtime_selector_authority=selector,
        opening_release=release,
        opening_release_root_sha256=release_root,
        opening_consumption=consumption,
        authorized_output_dir=release["authorized_output_dir"],
        output_dir=tmp_path / "holdout-fixed",
        run_one=run_one,
        failure_evidence=materialize_fixed_dp_failure_evidence,
        source_failure_evidence=materialize_source_ineligible_evidence,
        holdout_mode=True,
    )
    assert seen == list(FRESH_PLAN_ARMS[:2])
    assert report["complete_arm_run_count"] == 0
    assert report["retained_fixed_dp_capability_failure_count"] == 3
    terminals = json.loads(
        (tmp_path / "holdout-fixed" / "run_terminals.json").read_text(
            encoding="utf-8"
        )
    )
    assert {
        terminal["scientific_terminal"]["status"] for terminal in terminals
    } == {"fixed_dp_candidate_generation_capability_failure"}
    for run_dir in (tmp_path / "holdout-fixed" / "runs").iterdir():
        assert (run_dir / "fixed_dp_failure_receipt.json").is_file()


def test_generic_holdout_source_failure_terminates_before_other_arms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_projection(monkeypatch)
    release, release_root, consumption, selector = _holdout_opening()
    failure = RetainedScenarioCapabilityFailure(
        scenario_id="scenario-0",
        family="lead_vehicle_hard_brake",
        source_class="mapped_signal",
        phase_authority_mode="observe_same_tick_request",
        reason=(
            ScenarioCapabilityReason.MAPPED_CURRENT_SIGNAL_SOURCE_UNAVAILABLE
        ),
    )
    seen: list[str] = []

    def run_one(config: dict, _run_dir: Path) -> dict:
        seen.append(config["plan_arm"])
        raise failure

    report = _execute_validated_fresh_units(
        plan=_mini_plan(),
        qualification_rows=[{"route_identity_sha256": "e" * 64}],
        probe_template={},
        prepared_runtime_by_scenario={"d" * 64: {}},
        route_asset_by_identity={"e" * 64: {}},
        dp_repo=tmp_path / "dp",
        runtime_selector_authority=selector,
        opening_release=release,
        opening_release_root_sha256=release_root,
        opening_consumption=consumption,
        authorized_output_dir=release["authorized_output_dir"],
        output_dir=tmp_path / "holdout-source",
        run_one=run_one,
        failure_evidence=materialize_fixed_dp_failure_evidence,
        source_failure_evidence=materialize_source_ineligible_evidence,
        holdout_mode=True,
    )
    assert seen == [FRESH_PLAN_ARMS[0]]
    assert report["complete_arm_run_count"] == 0
    assert report["retained_source_ineligible_count"] == 3
    terminals = json.loads(
        (tmp_path / "holdout-source" / "run_terminals.json").read_text(
            encoding="utf-8"
        )
    )
    assert {
        terminal["scientific_terminal"]["status"] for terminal in terminals
    } == {"source_ineligible"}


def test_independent_failure_pair_authority_binds_config_and_cross_arm_reset() -> None:
    initial_input = "5" * 64
    initial_state = hashlib.sha256(
        ("v21_native_scene_context_v1\0" + initial_input).encode("ascii")
    ).hexdigest()
    spawn = {"seed": 25401, "max_steps": 64}
    spawn_sha = hashlib.sha256(
        json.dumps(spawn, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    authority = {
        "route_identity_sha256": "e" * 64,
        "semantic_parameter_block_sha256": "f" * 64,
        "native_route_sha256": "1" * 64,
        "logical_map_sha256": "2" * 64,
        "scenario_seed": 25401,
        "spawn_config_sha256": spawn_sha,
        "initial_state_sha256": initial_state,
        "initial_input_sha256": initial_input,
    }
    config = {
        "signal_complete_plan_authority": {
            "route_identity_sha256": "e" * 64,
            "semantic_parameter_block_sha256": "f" * 64,
        },
        "routes": [{"sha256": "1" * 64}],
        "map": {"sha256": "2" * 64},
        "seeds": {"scenario": 25401},
        "spawn_config": {"seed": 25401},
    }
    qualification = {
        "route_identity_sha256": "e" * 64,
        "semantic_parameter_block_sha256": "f" * 64,
    }
    _review_failure_pair_authority(
        {"pair_authority": authority},
        expected_config=config,
        qualification_row=qualification,
    )
    rows = [
        {"pair_key": "pair", "arm": arm, **authority}
        for arm in ("candidate0", "static14d", "scene14d")
    ]
    _validate_cross_arm_pair_authority(rows)

    rows[1]["initial_input_sha256"] = "9" * 64
    with pytest.raises(ValueError, match="cross-arm pair authority drifted"):
        _validate_cross_arm_pair_authority(rows)


def test_three_arm_core_does_not_retain_untyped_runner_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_projection(monkeypatch)
    plan = _mini_plan()
    release, release_root, consumption, roots = _opening()

    with pytest.raises(ValueError, match="ordinary runner failure"):
        _execute_validated_fresh_units(
            plan=plan,
            qualification_rows=[{"route_identity_sha256": "e" * 64}],
            probe_template={},
            prepared_runtime_by_scenario={"d" * 64: {}},
            route_asset_by_identity={"e" * 64: {}},
            dp_repo=tmp_path / "dp",
            runtime_selector_authority=roots,
            opening_release=release,
            opening_release_root_sha256=release_root,
            opening_consumption=consumption,
            authorized_output_dir=release["authorized_output_dir"],
            output_dir=tmp_path / "execution",
            run_one=lambda _config, _run_dir: (_ for _ in ()).throw(
                ValueError("ordinary runner failure")
            ),
            failure_evidence=lambda *_args: {},
        )


def test_public_three_arm_executor_requires_full_frozen_denominator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = __import__(
        "camp_core.integrations.diffusion_planner_v25_fresh_execution",
        fromlist=["unused"],
    )
    monkeypatch.setattr(
        module, "validate_signal_complete_execution_plan", lambda _plan: _mini_plan()
    )
    with pytest.raises(ValueError, match="denominator drifted"):
        execute_fresh_b2_three_arm_units(
            plan={},
            qualification_rows=[],
            probe_template={},
            prepared_runtime_by_scenario={},
            route_asset_by_identity={},
            dp_repo=tmp_path / "dp",
            runtime_selector_authority={},
            opening_release={},
            opening_release_root_sha256="0" * 64,
            opening_consumption={},
            authorized_output_dir="/root/autodl-tmp/unused",
            output_dir=tmp_path / "unused",
            run_one=lambda _config, _run_dir: {},
            failure_evidence=lambda *_args: {},
        )
