from __future__ import annotations

import copy
import importlib
import json
import sys
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_causal_atoms import (
    materialization_phase_receipt_not_available,
)
from camp_core.integrations.diffusion_planner_v26_target_bounded_surface import (
    ACTION_STABILITY_NOT_EVALUATED,
    CLOSED_LOOP_COMPUTE_SCOPE,
    DRY_RUN_RECEIPT_SCHEMA_VERSION,
    PRODUCTION_SURFACE_ID,
    SUPPORT_NOT_EVALUATED,
    V26_STAGE2_ALLOWED_CHANGED_FILES,
    build_target_bounded_dry_run_receipt,
    build_target_bounded_tick_receipt,
    production_surface_manifest,
    validate_production_surface_manifest,
    validate_production_surface_options,
    validate_prospective_action_stability_receipt,
    validate_prospective_support_ood_receipt,
    validate_v26_stage2_authority,
    validate_target_bounded_dry_run_receipt,
    validate_target_bounded_tick_receipt,
)


OPTIONS = {
    "adaptation_diagnostics": False,
    "sequential_forward_enabled": False,
    "replay_extra_forward_enabled": False,
    "guidance_policy": "disabled",
    "evaluate_all_arms": False,
}


def _selector_receipt() -> dict[str, object]:
    return {
        "status": "ok",
        "selected_index": 2,
        "selected_row_sha256": "c" * 64,
        "physical_feasible_mask": [True] * 8,
        "source_valid_mask": [True] * 8,
        "margin_best_vs_runner_up": 0.25,
        "exact_tie_set": [2],
    }


def _tick_receipt(
    *,
    selector_receipt: dict[str, object] | None = None,
    simulator_selected_row_sha256: str | None = "c" * 64,
) -> dict[str, object]:
    return build_target_bounded_tick_receipt(
        production_surface_id=PRODUCTION_SURFACE_ID,
        options=OPTIONS,
        operational_arm="Static14D",
        tick_index=0,
        state_sha256="a" * 64,
        candidate_pool_sha256_before="b" * 64,
        candidate_pool_sha256_after="b" * 64,
        primary_forward_count=1,
        sequential_forward_count=0,
        zero_call_receipt={
            "dp_or_model_calls_after_pool": 0,
            "latent_replacements_after_pool": 0,
            "candidate_generations_after_pool": 0,
        },
        selector_receipt=(
            _selector_receipt() if selector_receipt is None else selector_receipt
        ),
        simulator_selected_row_sha256=simulator_selected_row_sha256,
        materialization_phase_receipt=materialization_phase_receipt_not_available(),
    )


def test_production_manifest_rejects_diagnostic_and_extra_forward_options() -> None:
    manifest = production_surface_manifest(
        production_surface_id=PRODUCTION_SURFACE_ID,
        options=OPTIONS,
    )
    assert validate_production_surface_manifest(manifest) == manifest
    for name, value in (
        ("adaptation_diagnostics", True),
        ("sequential_forward_enabled", True),
        ("replay_extra_forward_enabled", True),
        ("guidance_policy", "preserve_candidate0"),
        ("evaluate_all_arms", True),
    ):
        bad = dict(OPTIONS)
        bad[name] = value
        with pytest.raises(ValueError):
            validate_production_surface_options(
                production_surface_id=PRODUCTION_SURFACE_ID,
                options=bad,
            )


def test_dry_run_receipt_is_zero_call_and_non_executing() -> None:
    receipt = build_target_bounded_dry_run_receipt(
        manifest=production_surface_manifest(
            production_surface_id=PRODUCTION_SURFACE_ID,
            options=OPTIONS,
        )
    )
    assert validate_target_bounded_dry_run_receipt(receipt) == receipt
    assert receipt == {
        "schema_version": DRY_RUN_RECEIPT_SCHEMA_VERSION,
        "dry_run": True,
        "execution_status": "dry_run_no_model_invocation",
        "production_surface_id": PRODUCTION_SURFACE_ID,
        "normalized_execution_options": OPTIONS,
        "invocation_counts": {
            "model": 0,
            "dp": 0,
            "latent": 0,
            "generation": 0,
            "simulator": 0,
        },
    }
    assert not {
        "selected_index",
        "selected_row_sha256",
        "support_status",
        "ood_status",
        "action_stability_status",
        "claim_authorized",
    } & set(receipt)
    bad = copy.deepcopy(receipt)
    bad["invocation_counts"]["model"] = 1
    with pytest.raises(ValueError, match="zero runtime invocations"):
        validate_target_bounded_dry_run_receipt(bad)


def test_target_runner_dry_run_short_circuits_runtime_and_legacy_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v25_industrial_bounded_closed_loop"
    )
    manifest_path = tmp_path / "v26_target_manifest.json"
    manifest_path.write_text(
        json.dumps(
            production_surface_manifest(
                production_surface_id=PRODUCTION_SURFACE_ID,
                options=OPTIONS,
            )
        ),
        encoding="utf-8",
    )

    def runtime_sentinel(*_args: object, **_kwargs: object) -> None:
        pytest.fail("dry-run reached a model, DP, simulator, or legacy-preflight adapter")

    for name in (
        "preflight",
        "execute",
        "evaluate",
        "validate_v26_stage2_authority",
        "_tracked_changes",
        "_install_fixed_dp_annotation_compatibility",
        "_run_one",
        "load_v25_runtime_selector_assets",
        "_interpreter_receipt",
        "_write_with_arrays",
    ):
        monkeypatch.setattr(runner, name, runtime_sentinel)
    monkeypatch.setattr(
        sys,
        "argv",
        ["target-bounded-runner", "dry-run", "--manifest", str(manifest_path)],
    )

    assert runner.main() == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["execution_status"] == "dry_run_no_model_invocation"
    assert receipt["invocation_counts"] == {
        "model": 0,
        "dp": 0,
        "latent": 0,
        "generation": 0,
        "simulator": 0,
    }


def test_target_runner_dry_run_rejects_extra_forward_option(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v25_industrial_bounded_closed_loop"
    )
    options = dict(OPTIONS)
    options["replay_extra_forward_enabled"] = True
    manifest_path = tmp_path / "invalid_v26_target_manifest.json"
    manifest_path.write_text(
        json.dumps(
            production_surface_manifest(
                production_surface_id=PRODUCTION_SURFACE_ID,
                options=OPTIONS,
            )
            | {"execution_options": options}
        ),
        encoding="utf-8",
    )

    def runtime_sentinel(*_args: object, **_kwargs: object) -> None:
        pytest.fail("rejected dry-run reached a model, DP, simulator, or legacy-preflight adapter")

    for name in (
        "preflight",
        "execute",
        "evaluate",
        "validate_v26_stage2_authority",
        "_tracked_changes",
        "_install_fixed_dp_annotation_compatibility",
        "_run_one",
        "load_v25_runtime_selector_assets",
        "_interpreter_receipt",
        "_write_with_arrays",
    ):
        monkeypatch.setattr(runner, name, runtime_sentinel)
    monkeypatch.setattr(
        sys,
        "argv",
        ["target-bounded-runner", "dry-run", "--manifest", str(manifest_path)],
    )
    with pytest.raises(ValueError, match="rejects replay extra forwards"):
        runner.main()


def test_production_callback_rejects_actual_execution_flag_drift() -> None:
    from scripts.integrations.validate_diffusion_planner_v25_fair_nonholdout import (
        _FairPredictBatch,
    )

    callback = object.__new__(_FairPredictBatch)
    with pytest.raises(ValueError, match="exactly bind callback execution flags"):
        _FairPredictBatch.__init__(
            callback,
            model=None,
            model_args=None,
            tensor_converter=None,
            fixed_dp_repo=Path("."),
            fixed_config={},
            route_sha256="a" * 64,
            builder=None,
            route_ids=[],
            replay=None,
            assets=None,
            state=None,
            max_ticks=0,
            operational_arm="Static14D",
            evaluate_all_arms=True,
            adaptation_diagnostics=False,
            causal_signal_chain=None,
            production_surface_id=PRODUCTION_SURFACE_ID,
            production_surface_options=OPTIONS,
        )


def test_production_callback_rejects_explicit_extra_selector_inventory() -> None:
    from scripts.integrations.validate_diffusion_planner_v25_fair_nonholdout import (
        _FairPredictBatch,
    )

    callback = object.__new__(_FairPredictBatch)
    with pytest.raises(ValueError, match="rejects explicit selector arm inventories"):
        _FairPredictBatch.__init__(
            callback,
            model=None,
            model_args=None,
            tensor_converter=None,
            fixed_dp_repo=Path("."),
            fixed_config={},
            route_sha256="a" * 64,
            builder=None,
            route_ids=[],
            replay=None,
            assets=None,
            state=None,
            max_ticks=0,
            operational_arm="Static14D",
            evaluate_all_arms=False,
            adaptation_diagnostics=False,
            causal_signal_chain=None,
            evaluation_arms=("Static14D", "Scene14D", "Static9D"),
            production_surface_id=PRODUCTION_SURFACE_ID,
            production_surface_options=OPTIONS,
        )


def test_target_tick_receipt_is_single_forward_per_arm_and_fail_closed() -> None:
    receipt = _tick_receipt()
    assert validate_target_bounded_tick_receipt(receipt) == receipt
    assert receipt["closed_loop_compute_scope"] == CLOSED_LOOP_COMPUTE_SCOPE
    assert receipt["candidate_pool"] == {
        "pool_sha256": "b" * 64,
        "candidate0_row": 0,
        "candidate_pool_mutation_count": 0,
    }
    assert receipt["forward_topology"] == {
        "primary_forward_count": 1,
        "sequential_forward_count": 0,
        "post_pool_model_forward_count": 0,
        "post_pool_dp_forward_count": 0,
        "post_pool_latent_replacement_count": 0,
        "post_pool_candidate_generation_count": 0,
        "trajectory_regeneration_count": 0,
    }
    selector = receipt["selector"]
    assert selector["pool_sha256"] == "b" * 64
    assert selector["source_valid_mask"] == [True] * 8
    assert selector["margin_best_vs_runner_up"] == 0.25
    assert selector["exact_tie_set"] == [2]
    assert selector["selected_index"] == 2
    assert receipt["simulator_selected_row"]["matches_candidate_row"] is True
    assert {
        row["status"]
        for row in receipt["atom_materialization_phase_receipt"].values()
    } == {"not_available"}
    assert not any("cross_arm" in key for key in receipt)

    for mutate in (
        lambda value: value["forward_topology"].__setitem__(
            "primary_forward_count", 2
        ),
        lambda value: value["simulator_selected_row"].__setitem__(
            "simulator_row_sha256", "d" * 64
        ),
        lambda value: value.__setitem__("cross_arm_tick_pool_equality", False),
    ):
        bad = copy.deepcopy(receipt)
        mutate(bad)
        with pytest.raises(ValueError):
            validate_target_bounded_tick_receipt(bad)


def test_successful_receipt_rejects_empty_action_identity() -> None:
    bad_selector = _selector_receipt()
    bad_selector["selected_index"] = None
    bad_selector["selected_row_sha256"] = None
    with pytest.raises(ValueError, match="successful selector requires a frozen action identity"):
        _tick_receipt(
            selector_receipt=bad_selector,
            simulator_selected_row_sha256=None,
        )

    bad_receipt = _tick_receipt()
    bad_receipt["selector"]["selected_index"] = None
    bad_receipt["selector"]["selected_row_sha256"] = None
    bad_receipt["simulator_selected_row"].update(
        {
            "selected_index": None,
            "candidate_row_sha256": None,
            "simulator_row_sha256": None,
        }
    )
    bad_receipt["prospective_action_stability"]["action_identity"] = {
        "selected_index": None,
        "selected_row_sha256": None,
    }
    with pytest.raises(ValueError, match="successful selector requires a frozen action identity"):
        validate_target_bounded_tick_receipt(bad_receipt)


def test_support_ood_and_action_stability_are_only_prospective_defaults() -> None:
    receipt = _tick_receipt()
    support = receipt["prospective_support_ood"]
    action = receipt["prospective_action_stability"]
    assert support["frozen_reference_id"] is None
    assert support["frozen_reference_hash"] is None
    assert support["support_status"] == SUPPORT_NOT_EVALUATED
    assert support["ood_status"] == SUPPORT_NOT_EVALUATED
    assert action["preregistered_protocol_id"] is None
    assert action["action_stability_status"] == ACTION_STABILITY_NOT_EVALUATED
    assert action["selected_action_identity_is_action_stability"] is False

    bad_support = copy.deepcopy(support)
    bad_support["support_status"] = "in_support"
    with pytest.raises(ValueError):
        validate_prospective_support_ood_receipt(bad_support)
    bad_action = copy.deepcopy(action)
    bad_action["action_stability_status"] = "stable"
    with pytest.raises(ValueError):
        validate_prospective_action_stability_receipt(bad_action)


def test_target_runner_wires_only_the_v26_fail_closed_surface() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "integrations"
        / "run_diffusion_planner_v25_industrial_bounded_closed_loop.py"
    ).read_text("utf-8")
    for literal in (
        "production_surface_id=PRODUCTION_SURFACE_ID",
        "production_surface_options=V26_TARGET_BOUNDED_PRODUCTION_OPTIONS",
        '"adaptation_diagnostics": False',
        '"sequential_forward_enabled": False',
        '"replay_extra_forward_enabled": False',
        '"guidance_policy": "disabled"',
        "validate_v26_stage2_authority(",
        "LEGACY_V25_PRE_ARTIFACT_REPAIR_ALLOWLIST",
    ):
        assert literal in source
    assert "preserve_candidate0" not in source
    assert "post_divergence_cross_arm_input_or_pool_equality_claimed" not in source
    assert "cross_arm_tick_pool" not in source
    authority = validate_v26_stage2_authority(
        baseline_implementation_head="a" * 40,
        live_implementation_head="b" * 40,
        baseline_is_ancestor=True,
        changed_files=list(V26_STAGE2_ALLOWED_CHANGED_FILES),
    )
    assert authority["changed_files"] == sorted(V26_STAGE2_ALLOWED_CHANGED_FILES)
    with pytest.raises(ValueError):
        validate_v26_stage2_authority(
            baseline_implementation_head="a" * 40,
            live_implementation_head="b" * 40,
            baseline_is_ancestor=True,
            changed_files=[*V26_STAGE2_ALLOWED_CHANGED_FILES, "extra.py"],
        )
