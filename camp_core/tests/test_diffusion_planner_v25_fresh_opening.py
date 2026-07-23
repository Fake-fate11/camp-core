from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_v25_fresh_opening import (
    FRESH_B2_CONTROLLER_ROLES,
    freeze_fresh_b2_controller_decision,
    freeze_fresh_b2_opening_consumption,
    freeze_fresh_b2_opening_release,
    validate_fresh_b2_controller_decision,
    validate_fresh_b2_opening_consumption,
    validate_fresh_b2_opening_release,
)


def _release() -> dict:
    return freeze_fresh_b2_opening_release(
        implementation_source_head="1" * 40,
        pointer_head_at_release="2" * 40,
        controller_decision_root_sha256="3" * 64,
        calibration_contract_root_sha256="4" * 64,
        preopen_qualification_root_sha256="5" * 64,
        model_registry_sha256="6" * 64,
        training_scale_sha256="7" * 64,
        context_scaler_sha256="8" * 64,
        scenario_manifest_root_sha256="9" * 64,
        run_nonce="a" * 64,
        authorized_output_dir="/root/autodl-tmp/camp_dp_v25_fresh_b2_once",
    )


def _controller() -> dict:
    inputs = {
        role: {
            "path": f"/root/autodl-tmp/v25-fresh-{role}",
            "root_sha256": f"{index + 1:x}" * 64,
        }
        for index, role in enumerate(FRESH_B2_CONTROLLER_ROLES)
    }
    return freeze_fresh_b2_controller_decision(
        implementation_source_head="1" * 40,
        pointer_head_at_release="2" * 40,
        critical_implementation_manifest_sha256="a" * 64,
        input_artifacts=inputs,
        probe_template_path="/root/autodl-tmp/v25-fresh-probe.json",
        probe_template_sha256="b" * 64,
        dp_repo_path="/root/autodl-tmp/Diffusion-Planner",
        calibration_contract_root_sha256="c" * 64,
        preopen_qualification_root_sha256=inputs["preopen"]["root_sha256"],
        model_registry_sha256="d" * 64,
        training_scale_sha256="e" * 64,
        context_scaler_sha256="f" * 64,
        scenario_manifest_root_sha256=inputs["scenario_manifest"][
            "root_sha256"
        ],
        run_nonce="0" * 64,
        authorized_output_dir="/root/autodl-tmp/v25-fresh-production",
    )


def test_fresh_controller_decision_is_type_and_value_exact() -> None:
    decision = _controller()
    assert validate_fresh_b2_controller_decision(copy.deepcopy(decision)) == decision
    assert decision["paired_unit_count"] == 500
    assert decision["arm_run_count"] == 1500
    assert decision["tick_capacity"] == 96_000
    assert decision["fresh_b2_open_authorized"] is True
    assert decision["full_r_authorized"] is False

    for mutate in (
        lambda value: value.__setitem__("arm_run_count", 1499),
        lambda value: value.__setitem__("fresh_b2_open_authorized", 1),
        lambda value: value.__setitem__("unexpected", False),
    ):
        changed = copy.deepcopy(decision)
        mutate(changed)
        with pytest.raises(ValueError):
            validate_fresh_b2_controller_decision(changed)


def test_fresh_opening_requires_external_one_time_release_and_consumption() -> None:
    release = _release()
    assert validate_fresh_b2_opening_release(copy.deepcopy(release)) == release
    assert release["fresh_b2_open_authorized"] is True
    assert release["fresh_b2_opened"] is False
    assert release["controller_decision_root_sha256"] == "3" * 64

    consumption = freeze_fresh_b2_opening_consumption(
        opening_release=release,
        release_root_sha256="b" * 64,
        marker_sha256="c" * 64,
    )
    assert (
        validate_fresh_b2_opening_consumption(
            copy.deepcopy(consumption),
            opening_release=release,
            release_root_sha256="b" * 64,
        )
        == consumption
    )
    assert consumption["consumed_before_outcome_capable_operation"] is True
    assert consumption["fresh_b2_opened_once"] is True
    assert consumption["second_consumption_allowed"] is False


@pytest.mark.parametrize("bad_head", ("1" * 8, "1" * 39, "1" * 64, 1))
def test_fresh_opening_requires_full_git_commit_heads(bad_head: object) -> None:
    with pytest.raises(ValueError, match="40-hex Git commit"):
        freeze_fresh_b2_opening_release(
            implementation_source_head=bad_head,  # type: ignore[arg-type]
            pointer_head_at_release="2" * 40,
            controller_decision_root_sha256="3" * 64,
            calibration_contract_root_sha256="4" * 64,
            preopen_qualification_root_sha256="5" * 64,
            model_registry_sha256="6" * 64,
            training_scale_sha256="7" * 64,
            context_scaler_sha256="8" * 64,
            scenario_manifest_root_sha256="9" * 64,
            run_nonce="a" * 64,
            authorized_output_dir="/root/autodl-tmp/camp_dp_v25_fresh_b2_once",
        )


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda value: value.__setitem__("unexpected", False), "field set drifted"),
        (lambda value: value.__setitem__("fresh_b2_open_authorized", 1), "exact value drifted"),
        (lambda value: value.__setitem__("paired_arms", ["candidate0"]), "exact value drifted"),
    ],
)
def test_fresh_opening_release_mutations_fail_closed(mutate, match: str) -> None:
    value = _release()
    mutate(value)
    with pytest.raises(ValueError, match=match):
        validate_fresh_b2_opening_release(value)


@pytest.mark.parametrize(
    "path",
    [
        "camp_dp_v25_fresh_b2_once",
        "/tmp/camp_dp_v25_fresh_b2_once",
        "/root/autodl-tmp/../camp_dp_v25_fresh_b2_once",
        "/root/autodl-tmp/camp_dp_v25_fresh_b2_once/",
    ],
)
def test_fresh_opening_rejects_noncanonical_output(path: str) -> None:
    with pytest.raises(ValueError, match="output"):
        freeze_fresh_b2_opening_release(
            implementation_source_head="1" * 40,
            pointer_head_at_release="2" * 40,
            controller_decision_root_sha256="3" * 64,
            calibration_contract_root_sha256="4" * 64,
            preopen_qualification_root_sha256="5" * 64,
            model_registry_sha256="6" * 64,
            training_scale_sha256="7" * 64,
            context_scaler_sha256="8" * 64,
            scenario_manifest_root_sha256="9" * 64,
            run_nonce="a" * 64,
            authorized_output_dir=path,
        )


def test_fresh_opening_consumption_crosslinks_are_exact() -> None:
    release = _release()
    consumption = freeze_fresh_b2_opening_consumption(
        opening_release=release,
        release_root_sha256="b" * 64,
        marker_sha256="c" * 64,
    )
    for field, value in (
        ("run_nonce", "d" * 64),
        ("authorized_output_dir", "/root/autodl-tmp/other"),
        ("consumed_before_outcome_capable_operation", False),
        ("outcome_fields_consumed_before_nonce", ["collision"]),
    ):
        mutated = copy.deepcopy(consumption)
        mutated[field] = value
        with pytest.raises(ValueError, match="exact value drifted"):
            validate_fresh_b2_opening_consumption(
                mutated,
                opening_release=release,
                release_root_sha256="b" * 64,
            )
