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
