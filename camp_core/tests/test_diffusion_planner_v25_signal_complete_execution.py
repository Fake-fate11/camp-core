from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_v25_signal_complete_execution import (
    build_candidate0_calibration_config,
    build_fresh_b2_arm_config,
    build_paired_calibration_arm_config,
    validate_candidate0_calibration_config,
    validate_fresh_b2_arm_config,
    validate_paired_calibration_arm_config,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
    canonical_json_bytes,
    freeze_experiment_protocol,
    freeze_holdout_identity,
)
from camp_core.integrations.diffusion_planner_v25_holdout_execution import (
    freeze_holdout_arm_config_from_legacy,
    validate_holdout_arm_config,
)
from camp_core.integrations.diffusion_planner_v25_holdout_preflight import (
    deterministic_nonfresh_callback,
    freeze_nonfresh_preflight_authority,
    project_actual_native_preflight_callbacks,
    run_production_composition_preflight,
    validate_production_composition_preflight,
)
from scripts.integrations.freeze_diffusion_planner_v25_holdout_production_preflight import (
    build_artifact as build_holdout_preflight_artifact,
)
from scripts.integrations.freeze_diffusion_planner_v25_b3_production_preflight import (
    _fresh_runtime_selector_authority,
)
from scripts.integrations.review_diffusion_planner_v25_holdout_production_preflight import (
    review_artifact as review_holdout_preflight_artifact,
)
from camp_core.integrations.diffusion_planner_v25_fresh_opening import (
    freeze_fresh_b2_opening_consumption,
    freeze_fresh_b2_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (
    build_signal_complete_suite,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (
    build_signal_complete_runtime_case,
)


SHA = "1" * 64


def _materialize_maps(tmp_path: Path, split: str = "calibration") -> Path:
    suite = build_signal_complete_suite(split)
    for relative, payload in suite["map_payloads"].items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return tmp_path


def _probe(tmp_path: Path) -> dict:
    return {
        "fixed_dp": {
            "head": "7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "repo": str(tmp_path / "ignored"),
            "checkpoint": {"path": str(tmp_path / "model.pt"), "sha256": SHA},
            "args_json": {"path": str(tmp_path / "args.json"), "sha256": SHA},
            "native_source_sha256": {"replay.py": SHA},
        },
        "selector": {
            "atom_scales": {"path": str(tmp_path / "scales.json"), "sha256": SHA},
            "weights": {"path": str(tmp_path / "weights.json"), "sha256": SHA},
            "score_contract": "score_k(w)=a_k^T w",
            "nonnegative_simplex": True,
        },
        "spawn_config": {},
    }


def _config(tmp_path: Path) -> dict:
    map_root = _materialize_maps(tmp_path / "maps")
    plan = build_signal_complete_execution_plan("calibration")
    identity = plan["identities"][0]
    unit = next(
        row
        for row in plan["execution_units"]
        if row["scenario_identity_sha256"]
        == identity["scenario_identity_sha256"]
    )
    prepared = build_signal_complete_runtime_case(
        identity,
        map_artifact=map_root,
        seeds=plan["seeds"],
    )
    route_path = tmp_path / "route.pkl"
    route_path.write_bytes(b"route-placeholder")
    return build_candidate0_calibration_config(
        probe_template=_probe(tmp_path),
        prepared_runtime=prepared,
        execution_unit=unit,
        route_asset={
            "name": identity["route_identity_sha256"],
            "path": str(route_path),
            "sha256": SHA,
        },
        dp_repo=tmp_path / "Diffusion-Planner",
    )


def _fresh_config(tmp_path: Path, plan_arm: str) -> dict:
    map_root = _materialize_maps(tmp_path / "fresh_maps", "fresh_b2")
    plan = build_signal_complete_execution_plan("fresh_b2")
    identity = plan["identities"][0]
    unit = next(
        row
        for row in plan["execution_units"]
        if row["scenario_identity_sha256"]
        == identity["scenario_identity_sha256"]
    )
    prepared = build_signal_complete_runtime_case(
        identity,
        map_artifact=map_root,
        seeds=plan["seeds"],
    )
    route_path = tmp_path / "fresh_route.pkl"
    route_path.write_bytes(b"fresh-route-placeholder")
    authority = {
        "training_artifact": {
            "path": str(tmp_path / "training"),
            "root_sha256": "2" * 64,
        },
        "training_review_artifact": {
            "path": str(tmp_path / "training_review"),
            "root_sha256": "3" * 64,
        },
        "calibration_contract_root_sha256": "4" * 64,
        "preopen_qualification_root_sha256": "5" * 64,
        "scenario_manifest_root_sha256": "6" * 64,
        "model_registry_sha256": "7" * 64,
        "training_scale_sha256": "8" * 64,
        "context_scaler_sha256": "9" * 64,
        "atom_scales": {
            "path": str(tmp_path / "runtime_atom_scales.json"),
            "sha256": "a" * 64,
        },
        "static14d_weights": {
            "path": str(tmp_path / "static14d_runtime_weights.npy"),
            "sha256": "b" * 64,
        },
    }
    return build_fresh_b2_arm_config(
        probe_template=_probe(tmp_path),
        prepared_runtime=prepared,
        execution_unit=unit,
        plan_arm=plan_arm,
        route_asset={
            "name": identity["route_identity_sha256"],
            "path": str(route_path),
            "sha256": SHA,
        },
        dp_repo=tmp_path / "Diffusion-Planner",
        runtime_selector_authority=authority,
    )


def _calibration_selector_authority(tmp_path: Path) -> dict:
    return {
        "training_artifact": {
            "path": str(tmp_path / "training"),
            "root_sha256": "2" * 64,
        },
        "training_review_artifact": {
            "path": str(tmp_path / "training_review"),
            "root_sha256": "3" * 64,
        },
        "model_registry_sha256": "7" * 64,
        "training_scale_sha256": "a" * 64,
        "context_scaler_sha256": "9" * 64,
        "atom_scales": {
            "path": str(tmp_path / "runtime_atom_scales.json"),
            "sha256": "a" * 64,
        },
        "static14d_weights": {
            "path": str(tmp_path / "static14d_runtime_weights.npy"),
            "sha256": "b" * 64,
        },
    }


def _holdout_identity_and_protocol() -> tuple[dict, dict]:
    identity = freeze_holdout_identity(
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
    protocol = freeze_experiment_protocol(
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
    return identity, protocol


def _nonfresh_preflight_authority(
    identity: dict, protocol: dict
) -> dict:
    return freeze_nonfresh_preflight_authority(
        holdout_identity_sha256=identity["holdout_identity_sha256"],
        experiment_protocol_sha256=protocol["experiment_protocol_sha256"],
        fixture_artifact_root_sha256="f" * 64,
        fixture_recovery_root_sha256="e" * 64,
        fixture_recovery_review_root_sha256="d" * 64,
    )


@pytest.mark.parametrize(
    "plan_arm",
    (
        "candidate0_operational_default",
        "camp_static14d",
        "camp_scene14d_no_v2i",
    ),
)
def test_fresh_b3_holdout_arm_upgrade_preserves_production_config(
    tmp_path: Path, plan_arm: str
) -> None:
    identity, protocol = _holdout_identity_and_protocol()
    legacy = _fresh_config(tmp_path, plan_arm)
    config = freeze_holdout_arm_config_from_legacy(
        legacy_config=legacy,
        holdout_identity=identity,
        experiment_protocol=protocol,
    )
    assert validate_holdout_arm_config(config) == config
    assert config["protocol"]["holdout_split"] == "fresh_b3"
    assert config["holdout_authority"]["holdout_identity_sha256"] == identity[
        "holdout_identity_sha256"
    ]

    mutated = copy.deepcopy(config)
    mutated["protocol"]["candidate0_semantics"] = "native-ranked Top1"
    with pytest.raises(ValueError, match="protocol drifted"):
        validate_holdout_arm_config(mutated)


def test_b3_preflight_selector_binds_b3_plan_not_legacy_role_guess(
    tmp_path: Path,
) -> None:
    calibration = _fresh_config(
        tmp_path, "candidate0_operational_default"
    )["runtime_selector_authority"]
    result = _fresh_runtime_selector_authority(
        accepted_preopen={
            "upstream_bindings": {
                "calibration_freeze": {
                    "path": "/root/autodl-tmp/calibration-freeze",
                    "root_sha256": "8" * 64,
                }
            }
        },
        accepted_preopen_root_sha256="9" * 64,
        b3_execution_plan_sha256="a" * 64,
        calibration_selector=calibration,
    )
    assert result["calibration_contract_root_sha256"] == "8" * 64
    assert result["preopen_qualification_root_sha256"] == "9" * 64
    assert result["scenario_manifest_root_sha256"] == "a" * 64


def test_exact_production_preflight_runs_three_real_configs_and_callback(
    tmp_path: Path,
) -> None:
    identity, protocol = _holdout_identity_and_protocol()
    configs = {
        arm: freeze_holdout_arm_config_from_legacy(
            legacy_config=_fresh_config(tmp_path / arm, plan_arm),
            holdout_identity=identity,
            experiment_protocol=protocol,
        )
        for arm, plan_arm in {
            "candidate0": "candidate0_operational_default",
            "static14d": "camp_static14d",
            "scene14d": "camp_scene14d_no_v2i",
        }.items()
    }
    preflight = run_production_composition_preflight(
        holdout_identity=identity,
        experiment_protocol=protocol,
        nonfresh_preflight_authority=_nonfresh_preflight_authority(
            identity, protocol
        ),
        fixture_root_sha256="f" * 64,
        config_payloads=configs,
        native_callback=deterministic_nonfresh_callback,
    )
    assert validate_production_composition_preflight(preflight) == preflight
    assert preflight["tick_count"] == 192
    assert preflight["native_callback_receipts"]["candidate0"][0][
        "candidate0_pool_evidence_composed"
    ] is True
    assert preflight["native_callback_receipts"]["candidate0"][0][
        "latency_namespaces"
    ]["online_operational_latency_ms"]["atoms"] == 0.0
    assert preflight["native_callback_receipts"]["candidate0"][0][
        "latency_namespaces"
    ]["supplementary_evidence_latency_ms"]["atoms"] > 0.0
    fatal_paths = preflight["path_matrix"]["artifact_fatal"]
    assert set(fatal_paths) == {
        "before_nonce",
        "after_marker_before_run",
        "after_run_before_receipt",
        "after_receipt_before_seal",
    }
    assert fatal_paths["before_nonce"]["fresh_opened_once"] is False
    assert fatal_paths["after_marker_before_run"]["fresh_opened_once"] is True
    assert fatal_paths["after_receipt_before_seal"][
        "complete_arm_run_count"
    ] == 1
    assert all(
        row["full_denominator_formed"] is False
        for row in fatal_paths.values()
    )

    changed = copy.deepcopy(preflight)
    changed["native_callback_receipts"]["candidate0"][0][
        "action_committed_before_supplementary_evidence"
    ] = False
    with pytest.raises(ValueError, match="action_committed"):
        validate_production_composition_preflight(changed)


def test_actual_native_projection_separates_candidate0_action_and_pool(
    tmp_path: Path,
) -> None:
    identity, protocol = _holdout_identity_and_protocol()
    configs = {
        arm: freeze_holdout_arm_config_from_legacy(
            legacy_config=_fresh_config(tmp_path / arm, plan_arm),
            holdout_identity=identity,
            experiment_protocol=protocol,
        )
        for arm, plan_arm in {
            "candidate0": "candidate0_operational_default",
            "static14d": "camp_static14d",
            "scene14d": "camp_scene14d_no_v2i",
        }.items()
    }

    def tick(arm: str, index: int, *, diagnostic: bool = False) -> dict:
        input_sha = hashlib.sha256(f"input-{index}".encode()).hexdigest()
        action_sha = hashlib.sha256(f"action-{index}".encode()).hexdigest()
        pool_sha = hashlib.sha256(f"pool-{index}".encode()).hexdigest()
        latency = {
            "input_materialization": 1.0,
            "default_inference": 2.0,
            "hook_total": 12.0 if diagnostic else 10.0,
            "tracker": 1.0,
            "total_planning": 13.0 if diagnostic else 11.0,
        }
        if diagnostic or arm != "candidate0":
            latency.update(
                {
                    "candidate_inference": 4.0,
                    "atom_materialization": 2.0,
                    "selector": 1.0,
                }
            )
        if arm == "scene14d":
            latency.update({"context": 0.5, "scene_weight": 0.25})
        value = {
            "tick_index": index,
            "input_sha256": input_sha,
            "default_output_sha256": action_sha,
            "selected_trajectory_sha256": action_sha,
            "latency_ms": latency,
            "planning_started_ns": 1_000 + index * 100,
            "action_available_ns": 1_050 + index * 100,
            "receipt_projected_ns": 1_060 + index * 100,
        }
        if diagnostic or arm != "candidate0":
            value["candidate_tensor_sha256_before"] = pool_sha
        if arm == "candidate0" and not diagnostic:
            value.update(
                {
                    "candidate0_action_first": True,
                    "same_forward_claimed": False,
                }
            )
        if diagnostic:
            value["planning_started_ns"] = 100_000 + index * 100
        return value

    primary = {
        arm: {
            "status": "ok",
            "ticks": [tick(arm, index) for index in range(64)],
        }
        for arm in ("candidate0", "static14d", "scene14d")
    }
    diagnostic = {
        "status": "ok",
        "ticks": [
            tick("candidate0", index, diagnostic=True)
            for index in range(64)
        ],
    }
    projected = project_actual_native_preflight_callbacks(
        config_payloads=configs,
        primary_native_receipts=primary,
        candidate0_supplementary_native_receipt=diagnostic,
    )
    candidate0 = projected["candidate0"][0]
    assert candidate0["action_committed_before_supplementary_evidence"] is True
    assert candidate0["latency_namespaces"][
        "online_operational_latency_ms"
    ]["atoms"] == 0.0
    assert candidate0["latency_namespaces"][
        "supplementary_evidence_latency_ms"
    ]["atoms"] == 2.0
    assert candidate0["forward_binding"]["pool_evidence_mode"] == (
        "same_tick_same_base_forward_supplementary"
    )

    changed = copy.deepcopy(diagnostic)
    changed["ticks"][0]["input_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="base-forward"):
        project_actual_native_preflight_callbacks(
            config_payloads=configs,
            primary_native_receipts=primary,
            candidate0_supplementary_native_receipt=changed,
        )


def test_exact_production_preflight_artifact_is_sealed_and_independently_reviewed(
    tmp_path: Path,
) -> None:
    identity, protocol = _holdout_identity_and_protocol()
    identity_path = tmp_path / "holdout_identity.json"
    protocol_path = tmp_path / "experiment_protocol.json"
    identity_path.write_bytes(canonical_json_bytes(identity))
    protocol_path.write_bytes(canonical_json_bytes(protocol))
    authority_path = tmp_path / "preflight_authority.json"
    authority_path.write_bytes(
        canonical_json_bytes(
            _nonfresh_preflight_authority(identity, protocol)
        )
    )
    config_paths: dict[str, Path] = {}
    for arm, plan_arm in {
        "candidate0": "candidate0_operational_default",
        "static14d": "camp_static14d",
        "scene14d": "camp_scene14d_no_v2i",
    }.items():
        config = freeze_holdout_arm_config_from_legacy(
            legacy_config=_fresh_config(tmp_path / f"artifact-{arm}", plan_arm),
            holdout_identity=identity,
            experiment_protocol=protocol,
        )
        path = tmp_path / f"{arm}.json"
        path.write_bytes(canonical_json_bytes(config))
        config_paths[arm] = path
    source = tmp_path / "preflight"
    source_root = build_holdout_preflight_artifact(
        holdout_identity_path=identity_path,
        experiment_protocol_path=protocol_path,
        preflight_authority_path=authority_path,
        fixture_root_sha256="f" * 64,
        config_paths=config_paths,
        output_dir=source,
    )
    review = tmp_path / "preflight-review"
    review_root = review_holdout_preflight_artifact(
        source_artifact=source,
        source_root_sha256=source_root,
        output_dir=review,
    )
    assert len(source_root) == len(review_root) == 64
    report = json.loads((review / "report.json").read_text(encoding="utf-8"))
    assert (
        report["status"]
        == "passed_independent_production_composition_preflight_review"
    )


def _paired_calibration_config(tmp_path: Path, plan_arm: str) -> dict:
    map_root = _materialize_maps(tmp_path / "calibration_maps", "calibration")
    plan = build_signal_complete_execution_plan("calibration")
    identity = plan["identities"][0]
    base = next(
        row
        for row in plan["execution_units"]
        if row["scenario_identity_sha256"]
        == identity["scenario_identity_sha256"]
    )
    ordered_arms = [
        "candidate0_operational_default",
        "camp_static14d",
        "camp_scene14d_no_v2i",
    ]
    payload = {
        "scenario_identity_sha256": base["scenario_identity_sha256"],
        "seed": base["seed"],
        "ordered_arms": ordered_arms,
    }
    unit = {
        "unit_ordinal": base["unit_ordinal"],
        **payload,
        "unit_sha256": hashlib.sha256(
            (
                json.dumps(
                    payload,
                    sort_keys=True,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    allow_nan=False,
                )
                + "\n"
            ).encode("utf-8")
        ).hexdigest(),
    }
    prepared = build_signal_complete_runtime_case(
        identity,
        map_artifact=map_root,
        seeds=plan["seeds"],
    )
    route_path = tmp_path / "calibration_route.pkl"
    route_path.write_bytes(b"calibration-route-placeholder")
    return build_paired_calibration_arm_config(
        probe_template=_probe(tmp_path),
        prepared_runtime=prepared,
        execution_unit=unit,
        plan_arm=plan_arm,
        route_asset={
            "name": identity["route_identity_sha256"],
            "path": str(route_path),
            "sha256": SHA,
        },
        dp_repo=tmp_path / "Diffusion-Planner",
        runtime_selector_authority=_calibration_selector_authority(tmp_path),
    )


def _opening_authority(config: dict) -> dict:
    selector = config["runtime_selector_authority"]
    release = freeze_fresh_b2_opening_release(
        implementation_source_head="a" * 40,
        pointer_head_at_release="b" * 40,
        controller_decision_root_sha256="c" * 64,
        calibration_contract_root_sha256=selector[
            "calibration_contract_root_sha256"
        ],
        preopen_qualification_root_sha256=selector[
            "preopen_qualification_root_sha256"
        ],
        model_registry_sha256=selector["model_registry_sha256"],
        training_scale_sha256=selector["training_scale_sha256"],
        context_scaler_sha256=selector["context_scaler_sha256"],
        scenario_manifest_root_sha256=selector["scenario_manifest_root_sha256"],
        run_nonce="d" * 64,
        authorized_output_dir="/root/autodl-tmp/v25-fresh-b2-test",
    )
    release_root = "e" * 64
    consumption = freeze_fresh_b2_opening_consumption(
        opening_release=release,
        release_root_sha256=release_root,
        marker_sha256="f" * 64,
    )
    return {
        "opening_release": release,
        "opening_release_root_sha256": release_root,
        "opening_consumption": consumption,
    }


def test_candidate0_calibration_config_reaches_native_validator(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert validate_candidate0_calibration_config(config) == config

    from scripts.integrations import run_diffusion_planner_dp_camp_v21_native

    run_diffusion_planner_dp_camp_v21_native._validate_native_config(config)
    assert config["protocol"]["arm_order"] == ["dp"]
    assert config["protocol"]["fixed_k8_candidate0"] is True
    assert config["protocol"]["fresh_b2_opened"] is False
    assert config["signal_complete_runtime"]["outcome_fields_consumed"] == []


@pytest.mark.parametrize(
    ("plan_arm", "native_arm", "fixed_candidate0", "scene_provider"),
    [
        ("candidate0_operational_default", "dp", True, False),
        ("camp_static14d", "camp", False, False),
        ("camp_scene14d_no_v2i", "camp", False, True),
    ],
)
def test_paired_calibration_primary_arm_configs_bind_training_authority(
    tmp_path: Path,
    plan_arm: str,
    native_arm: str,
    fixed_candidate0: bool,
    scene_provider: bool,
) -> None:
    config = _paired_calibration_config(tmp_path, plan_arm)
    assert validate_paired_calibration_arm_config(config) == config
    protocol = config["protocol"]
    assert protocol["arm_order"] == [native_arm]
    assert protocol["fixed_k8_candidate0"] is fixed_candidate0
    assert protocol["calibration_authorized"] is True
    assert protocol["camp_method_outcomes_authorized"] is True
    assert protocol["fresh_b2_opened"] is False
    assert protocol["fresh_outcome_fields_consumed"] == []
    assert config["selector"]["scene_weight_provider_required"] is scene_provider
    assert config["signal_complete_runtime"]["outcome_fields_consumed"] == []


@pytest.mark.parametrize(
    ("path", "value", "match"),
    [
        (("protocol", "fresh_b2_opened"), True, "protocol"),
        (("protocol", "fixed_k8_candidate0"), False, "protocol"),
        (("selector", "weights", "sha256"), "c" * 64, "selector"),
        (
            ("runtime_selector_authority", "training_scale_sha256"),
            "d" * 64,
            "selector",
        ),
        (("signal_complete_plan_authority", "arm_order_index"), 1, "plan"),
        (("signal_complete_plan_authority", "seed"), 25401, "seed"),
    ],
)
def test_paired_calibration_arm_config_mutations_fail_closed(
    tmp_path: Path,
    path: tuple[object, ...],
    value: object,
    match: str,
) -> None:
    mutated = copy.deepcopy(
        _paired_calibration_config(tmp_path, "candidate0_operational_default")
    )
    target: object = mutated
    for part in path[:-1]:
        target = target[part]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    with pytest.raises(ValueError, match=match):
        validate_paired_calibration_arm_config(mutated)


@pytest.mark.parametrize(
    ("path", "value", "match"),
    [
        (("protocol", "fixed_k8_candidate0"), False, "protocol"),
        (("protocol", "arm_order"), ["dp", "camp"], "protocol"),
        (("protocol", "fresh_b2_opened"), True, "protocol"),
        (("signal_complete_plan_authority", "seed"), 25302, "seed"),
        (("signal_complete_plan_authority", "unit_sha256"), "2" * 64, "unit SHA"),
        (("routes", 0, "name"), "2" * 64, "runtime assets"),
    ],
)
def test_candidate0_calibration_config_mutations_fail_closed(
    tmp_path: Path,
    path: tuple[object, ...],
    value: object,
    match: str,
) -> None:
    mutated = copy.deepcopy(_config(tmp_path))
    target: object = mutated
    for part in path[:-1]:
        target = target[part]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    with pytest.raises(ValueError, match=match):
        validate_candidate0_calibration_config(mutated)


def test_native_runner_requires_canonical_candidate0_calibration_mode(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    from scripts.integrations import run_diffusion_planner_dp_camp_v21_native

    run_arm = run_diffusion_planner_dp_camp_v21_native.build_native_arm_runner(
        config,
        device="cpu",
    )
    route = config["routes"][0]
    with pytest.raises(ValueError, match="same-forward fixed-K8 candidate0"):
        run_arm(
            route=route,
            arm="dp",
            config=config,
            output_dir=tmp_path / "output",
            max_steps=64,
            fixed_k8_candidate0=False,
        )
    with pytest.raises(ValueError, match="cannot be injected"):
        run_arm(
            route=route,
            arm="dp",
            config=config,
            output_dir=tmp_path / "output",
            max_steps=64,
            fixed_k8_candidate0=True,
            scene_adapter=lambda scene, tick: {},
        )


@pytest.mark.parametrize(
    ("plan_arm", "native_arm", "fixed_candidate0", "scene_provider"),
    [
        ("candidate0_operational_default", "dp", True, False),
        ("camp_static14d", "camp", False, False),
        ("camp_scene14d_no_v2i", "camp", False, True),
    ],
)
def test_fresh_primary_arm_configs_bind_same_frozen_authority(
    tmp_path: Path,
    plan_arm: str,
    native_arm: str,
    fixed_candidate0: bool,
    scene_provider: bool,
) -> None:
    config = _fresh_config(tmp_path, plan_arm)
    assert validate_fresh_b2_arm_config(config) == config
    from scripts.integrations import run_diffusion_planner_dp_camp_v21_native

    run_diffusion_planner_dp_camp_v21_native._validate_native_config(config)
    protocol = config["protocol"]
    assert protocol["arm_order"] == [native_arm]
    assert protocol["fixed_k8_candidate0"] is fixed_candidate0
    assert protocol["candidate0_offline_pool_evidence_required"] is (
        plan_arm == "candidate0_operational_default"
    )
    assert protocol["external_one_time_opening_release_required"] is True
    assert protocol["execution_authorized_by_config"] is False
    assert protocol["fresh_b2_opened"] is False
    assert protocol["fresh_outcome_fields_consumed"] == []
    assert config["selector"]["scene_weight_provider_required"] is scene_provider
    assert config["signal_complete_runtime"]["outcome_fields_consumed"] == []


@pytest.mark.parametrize(
    ("path", "value", "match"),
    [
        (("protocol", "fresh_b2_opened"), True, "protocol"),
        (("protocol", "execution_authorized_by_config"), True, "protocol"),
        (("selector", "weights", "sha256"), "c" * 64, "selector"),
        (
            ("runtime_selector_authority", "atom_scales", "sha256"),
            "d" * 64,
            "selector",
        ),
        (("signal_complete_plan_authority", "arm_order_index"), 1, "plan"),
        (
            ("signal_complete_plan_authority", "semantic_parameter_block_sha256"),
            "2" * 64,
            "plan",
        ),
    ],
)
def test_fresh_arm_config_mutations_fail_closed(
    tmp_path: Path,
    path: tuple[object, ...],
    value: object,
    match: str,
) -> None:
    mutated = copy.deepcopy(
        _fresh_config(tmp_path, "candidate0_operational_default")
    )
    target: object = mutated
    for part in path[:-1]:
        target = target[part]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    with pytest.raises(ValueError, match=match):
        validate_fresh_b2_arm_config(mutated)


def test_fresh_native_runner_requires_consumed_opening_before_runtime(
    tmp_path: Path,
) -> None:
    config = _fresh_config(tmp_path, "candidate0_operational_default")
    from scripts.integrations import run_diffusion_planner_dp_camp_v21_native

    with pytest.raises(ValueError, match="one-time opening"):
        run_diffusion_planner_dp_camp_v21_native.build_native_arm_runner(
            config,
            device="cuda",
        )


def test_fresh_native_runner_rejects_arm_mode_drift_before_model_load(
    tmp_path: Path,
) -> None:
    from scripts.integrations import run_diffusion_planner_dp_camp_v21_native

    candidate0 = _fresh_config(tmp_path / "candidate0", "candidate0_operational_default")
    candidate_runner = run_diffusion_planner_dp_camp_v21_native.build_native_arm_runner(
        candidate0,
        device="cuda",
        fresh_b2_opening_authority=_opening_authority(candidate0),
    )
    with pytest.raises(ValueError, match="candidate0 mode"):
        candidate_runner(
            route=candidate0["routes"][0],
            arm="dp",
            config=candidate0,
            output_dir=tmp_path / "candidate0_output",
            max_steps=64,
            fixed_k8_candidate0=False,
        )

    static = _fresh_config(tmp_path / "static", "camp_static14d")
    static_runner = run_diffusion_planner_dp_camp_v21_native.build_native_arm_runner(
        static,
        device="cuda",
        fresh_b2_opening_authority=_opening_authority(static),
    )
    with pytest.raises(ValueError, match="Static14D mode"):
        static_runner(
            route=static["routes"][0],
            arm="camp",
            config=static,
            output_dir=tmp_path / "static_output",
            max_steps=64,
            v25_weight_provider=lambda _: {},
        )

    scene = _fresh_config(tmp_path / "scene", "camp_scene14d_no_v2i")
    scene_runner = run_diffusion_planner_dp_camp_v21_native.build_native_arm_runner(
        scene,
        device="cuda",
        fresh_b2_opening_authority=_opening_authority(scene),
    )
    with pytest.raises(ValueError, match="Scene14D mode"):
        scene_runner(
            route=scene["routes"][0],
            arm="camp",
            config=scene,
            output_dir=tmp_path / "scene_output",
            max_steps=64,
        )


def test_fresh_native_runner_rejects_fixed_dp_runtime_authority_drift(
    tmp_path: Path,
) -> None:
    from scripts.integrations import run_diffusion_planner_dp_camp_v21_native

    config = _fresh_config(tmp_path, "candidate0_operational_default")
    runner = run_diffusion_planner_dp_camp_v21_native.build_native_arm_runner(
        config,
        device="cuda",
        fresh_b2_opening_authority=_opening_authority(config),
    )
    mutated = copy.deepcopy(config)
    mutated["fixed_dp"]["repo"] = str(tmp_path / "alternate-fixed-dp")
    with pytest.raises(ValueError, match="fixed-DP runtime authority drifted"):
        runner(
            route=mutated["routes"][0],
            arm="dp",
            config=mutated,
            output_dir=tmp_path / "mutated-output",
            max_steps=64,
            fixed_k8_candidate0=True,
        )
