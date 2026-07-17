from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.atoms.driver_atoms import DriverAtomContext
from camp_core.integrations.diffusion_planner import CAMPSelector
from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact
from camp_core.integrations.diffusion_planner_causal_atoms import (
    source_valid_progress_shortfall,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (
    SIGNAL_CHAIN_SCHEMA_VERSION,
    build_runtime_signal_receipt,
    build_semantic_clone_payload,
    canonical_json_sha256,
    validate_signal_chain,
)
from scripts.integrations import (
    build_diffusion_planner_v25_static_atom_ledger as builder,
    review_diffusion_planner_v25_r0_authority_source as source_reviewer,
    run_diffusion_planner_v25_controlled_training_corpus as corpus,
    validate_diffusion_planner_v25_static_atom_ledger as validator,
)


def _case() -> dict:
    return {
        "scenario_id": "1" * 64,
        "route_identity_sha256": "2" * 64,
        "source_map_sha256": "3" * 64,
        "source_map_path": "/source/export/map.osm",
        "source_family": "source_a",
        "repository": "repo_a",
        "map_family_id": "map_a",
        "route_family_id": "route_a",
        "parameter_block_id": "block_a",
        "split": "train",
        "seed": 25001,
        "family": "red_light_phase_timing",
        "tier": "borderline",
        "semantic_variant": "red_straight",
        "parameters": {"ego_speed_mps": 8.0, "variant": 4},
        "actors": [],
        "signal": {
            "phase": "red",
            "mapped_source_required": True,
        },
    }


def _semantic_and_chain() -> tuple[dict, dict]:
    case = _case()
    route = np.column_stack((np.linspace(0.0, 100.0, 101), np.zeros(101)))
    stop = np.asarray([[20.0, -2.0], [20.0, 2.0]], dtype=np.float64)
    semantic = build_semantic_clone_payload(
        case, route_polyline_world=route, stop_line_world=stop
    )
    chain = {
        "schema_version": SIGNAL_CHAIN_SCHEMA_VERSION,
        "scenario_id": case["scenario_id"],
        "route_identity_sha256": case["route_identity_sha256"],
        "source_map_sha256": case["source_map_sha256"],
        "regulatory_element_ids": [10],
        "physical_light_ids": [11],
        "bulb_ids": [12],
        "controlled_lanelet_ids": [20],
        "route_lanelet_ids": [20, 21],
        "route_geometry_sha256": canonical_json_sha256(
            {
                "route_polyline_local_m": semantic["route_polyline_local_m"],
                "stop_line_local_m": semantic["stop_line_local_m"],
            }
        ),
        "stop_line_id": 13,
        "stop_line_geometry_m": stop.tolist(),
        "stop_line_geometry_sha256": canonical_json_sha256(stop.tolist()),
        "stop_line_route_distance_m": 0.01,
        "route_arc_m": 20.0,
        "route_length_m": 100.0,
        "route_tangent_world": [1.0, 0.0],
        "expected_current_phase": "red",
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": canonical_json_sha256(semantic),
        "source_chain_sha256": "",
    }
    chain["source_chain_sha256"] = canonical_json_sha256(
        {key: value for key, value in chain.items() if key != "source_chain_sha256"}
    )
    return semantic, chain


def _rehash_chain(chain: dict) -> dict:
    chain["source_chain_sha256"] = canonical_json_sha256(
        {key: value for key, value in chain.items() if key != "source_chain_sha256"}
    )
    return chain


def test_source_valid_progress_reference_handles_reachable_masks_and_empty() -> None:
    progress = np.asarray([10.0, 12.0, 8.0, 11.0])
    reference, cost = source_valid_progress_shortfall(
        progress, np.asarray([True, False, True, True])
    )
    assert reference == 11.0
    np.testing.assert_array_equal(cost, [1.0, 0.0, 3.0, 0.0])
    reference, cost = source_valid_progress_shortfall(
        progress, np.ones(4, dtype=bool)
    )
    assert reference == 12.0
    np.testing.assert_array_equal(cost, [2.0, 0.0, 4.0, 1.0])
    with pytest.raises(ValueError, match="empty"):
        source_valid_progress_shortfall(progress, np.zeros(4, dtype=bool))
    with pytest.raises(ValueError, match="strict booleans"):
        source_valid_progress_shortfall(progress, [1, 0, 1, 1])


def test_static14d_uses_source_valid_when_every_candidate_is_physically_bad() -> None:
    selector = CAMPSelector(
        atom_scales=np.ones(14),
        static_weights=np.ones(14),
        mode="static",
        fallback_mode="top1",
    )
    t = np.arange(80, dtype=np.float64) * 0.1
    candidates = np.zeros((8, 80, 4), dtype=np.float64)
    for index in range(8):
        candidates[index, :, 0] = t * (1.0 + 0.1 * index)
    context = DriverAtomContext(
        dt=0.1,
        lane_centerline=np.column_stack((np.linspace(0.0, 100.0, 101), np.zeros(101))),
        speed_limit=20.0,
    )
    source_valid = np.zeros(8, dtype=bool)
    source_valid[2] = True
    result = selector.select(
        candidates,
        context,
        candidate_progress=np.arange(8, dtype=np.float64),
        candidate_planned_red_light_cost=np.zeros(8),
        candidate_red_stopping_margin_cost=np.zeros(8),
        candidate_dp_prior_jerk_excess_cost=np.zeros(8),
        candidate_source_valid_mask=source_valid,
        external_feasible_mask=np.zeros(8, dtype=bool),
        apply_context_feasibility=False,
    )
    assert result.selected_index == 2
    assert result.used_fallback is False
    assert not result.physical_feasible_mask.any()
    np.testing.assert_array_equal(result.source_valid_mask, source_valid)

    with pytest.raises(ValueError, match="source_valid candidate set is empty"):
        selector.select(
            candidates,
            context,
            candidate_progress=np.arange(8, dtype=np.float64),
            candidate_planned_red_light_cost=np.zeros(8),
            candidate_red_stopping_margin_cost=np.zeros(8),
            candidate_dp_prior_jerk_excess_cost=np.zeros(8),
            candidate_source_valid_mask=np.zeros(8, dtype=bool),
            external_feasible_mask=np.zeros(8, dtype=bool),
            apply_context_feasibility=False,
        )


def test_semantic_clone_hash_ignores_source_and_id_clones_but_not_geometry() -> None:
    case = _case()
    route = np.column_stack((np.linspace(0.0, 100.0, 101), np.zeros(101)))
    stop = np.asarray([[20.0, -2.0], [20.0, 2.0]], dtype=np.float64)
    baseline = build_semantic_clone_payload(
        case, route_polyline_world=route, stop_line_world=stop
    )
    clone = copy.deepcopy(case)
    clone.update(
        scenario_id="4" * 64,
        route_identity_sha256="5" * 64,
        source_map_sha256="6" * 64,
        source_map_path="/different/export.osm",
        source_family="source_b",
        repository="repo_b",
        map_family_id="map_b",
        route_family_id="route_b",
        parameter_block_id="block_b",
        split="calibration",
        seed=999,
    )
    cloned_payload = build_semantic_clone_payload(
        clone, route_polyline_world=route + [1000.0, -500.0], stop_line_world=stop + [1000.0, -500.0]
    )
    assert canonical_json_sha256(cloned_payload) == canonical_json_sha256(baseline)
    changed = route.copy()
    changed[:, 1] = 0.01 * changed[:, 0] ** 2
    changed_payload = build_semantic_clone_payload(
        case, route_polyline_world=changed, stop_line_world=stop
    )
    assert canonical_json_sha256(changed_payload) != canonical_json_sha256(baseline)


@pytest.mark.parametrize(
    "mutation,pattern",
    [
        (lambda chain: chain.update(regulatory_element_ids=[10, 99]), "ambiguous"),
        (lambda chain: chain.pop("stop_line_id"), "field set"),
        (lambda chain: chain.update(route_arc_m=101.0), "route-arc"),
        (lambda chain: chain.update(controlled_lanelet_ids=[99]), "inconsistent"),
    ],
)
def test_red_signal_chain_mutations_fail_closed(mutation, pattern: str) -> None:
    _semantic, original = _semantic_and_chain()
    chain = copy.deepcopy(original)
    mutation(chain)
    if "source_chain_sha256" in chain:
        _rehash_chain(chain)
    with pytest.raises(ValueError, match=pattern):
        validate_signal_chain(chain)


def test_runtime_signal_receipt_rejects_phase_or_lanelet_mismatch() -> None:
    _semantic, chain = _semantic_and_chain()
    with pytest.raises(ValueError, match="current phase"):
        build_runtime_signal_receipt(
            chain,
            scenario_id=chain["scenario_id"],
            tick_index=0,
            decision_time_s=0.0,
            current_phase="green",
            applied_route_lanelet_ids=[20],
            applied_map_lanelet_ids=[],
        )
    with pytest.raises(ValueError, match="wrong or absent"):
        build_runtime_signal_receipt(
            chain,
            scenario_id=chain["scenario_id"],
            tick_index=0,
            decision_time_s=0.0,
            current_phase="red",
            applied_route_lanelet_ids=[999],
            applied_map_lanelet_ids=[],
        )


def test_full_r_executor_cannot_self_authorize_without_ultra_chain() -> None:
    with pytest.raises(ValueError, match="Ultra preflight release"):
        corpus._verify_full_r_authority(
            r0_review_artifact=None,
            r0_review_root_sha256=None,
            r0_source_artifact=None,
            r0_source_root_sha256=None,
            preflight_release_artifact=None,
            preflight_release_root_sha256=None,
            preflight_artifact=None,
            preflight_review_artifact=None,
            preflight_review_root_sha256=None,
            execute_release_artifact=None,
            execute_release_root_sha256=None,
            camp_head="a" * 40,
            mode="preflight",
        )


def test_r0_source_reviewer_serializes_numpy_check_results_as_native_bool() -> None:
    checks = source_reviewer._native_bool_checks(
        {"numpy_true": np.bool_(True), "numpy_false": np.bool_(False)}
    )
    assert checks == {"numpy_true": True, "numpy_false": False}
    assert all(type(value) is bool for value in checks.values())


def _write_stage_a_inputs(tmp_path: Path) -> tuple[Path, str, Path, str]:
    a0 = tmp_path / "a0"
    a0.mkdir()
    a0_report = {
        "schema_version": builder.A0_SCHEMA_VERSION,
        "status": "passed",
        "stage": "A0_authority_hardening",
        "stage_a0_code_head": "0" * 40,
        "released_s01_source_head": "1" * 40,
        "released_s01_final_baseline_head": "2" * 40,
        "fixed_dp_head": builder.FIXED_DP_HEAD,
        "strict_inventory": {},
        "probe_authority": {},
        "rejected_roots": [builder.SUPERSEDED_PARTIAL_CORPUS_ROOT],
        "failed_preflight_role": "diagnostic_only_training_calibration_evaluation_ineligible",
        "existing_3x64_model_rerun": False,
        "gpu_work_started": False,
        "stage_a_authorized": True,
        "r_authorized": False,
        "training_authorized": False,
        "calibration_authorized": False,
        "scene_runtime_authorized": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    (a0 / "report.json").write_text(
        json.dumps(a0_report)
        + "\n",
        encoding="utf-8",
    )
    (a0 / "HEADS").write_text(
        f"camp_head={'0' * 40}\nfixed_dp_head={builder.FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (a0 / "run.exit").write_text("0\n", encoding="ascii")
    a0_root = seal_artifact(a0, label="test a0")
    decision = tmp_path / "decision"
    decision.mkdir()
    decision_payload = {
        "schema_version": "camp_dp_v25_ultra_stage_a11_r01_decision_v2",
        "status": "A1_1_R0_1_only_released",
        "decision_date": "2026-07-17",
        "source_thread_id": "test",
        "corrected_source_head": "a" * 40,
        "fixed_dp_head": builder.FIXED_DP_HEAD,
        "s01_preflight_root_sha256": "3" * 64,
        "s01_review_root_sha256": "4" * 64,
        "a0_root_sha256": a0_root,
        "formal_root_sha256": builder.FORMAL_ROOT_SHA256,
        "rejected_roots": [builder.SUPERSEDED_PARTIAL_CORPUS_ROOT],
        "superseded_diagnostic_roots": ["5" * 64],
        "progress_reference": "source_valid_candidate_set_reference",
        "progress_formula": "r=max(progress[j] where source_valid[j]); progress_shortfall[k]=max(r-progress[k],0)",
        "selection_eligibility": "source_valid",
        "empty_source_valid": "fail_closed",
        "candidate0_or_all_k_fallback_allowed": False,
        "a1_1_authorized": True,
        "r0_1_source_authority_preflight_authorized": True,
        "bounded_21red_1nosignal_x64_authorized_after_source_pass": True,
        "full_r_authorized": False,
        "monitor_authorized": False,
        "training_authorized": False,
        "calibration_authorized": False,
        "scene_runtime_authorized": False,
        "v2i_authorized": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    (decision / "decision.json").write_text(
        json.dumps(decision_payload)
        + "\n",
        encoding="utf-8",
    )
    (decision / "HEADS").write_text(
        f"camp_head={'a' * 40}\nfixed_dp_head={builder.FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (decision / "run.exit").write_text("0\n", encoding="ascii")
    decision_root = seal_artifact(decision, label="test decision")
    return a0, a0_root, decision, decision_root


def _write_ledger_artifact(
    path: Path, ledger: dict, fixture: dict
) -> str:
    path.mkdir()
    (path / "atom_ledger.json").write_text(
        json.dumps(ledger, sort_keys=True) + "\n", encoding="utf-8"
    )
    (path / "numeric_fixture.json").write_text(
        json.dumps(fixture, sort_keys=True) + "\n", encoding="utf-8"
    )
    (path / "run.exit").write_text("0\n", encoding="ascii")
    return seal_artifact(path, label="test A1 ledger")


@pytest.mark.parametrize("mutation", ["delete", "substitute_head", "substitute_a0"])
def test_a11_authority_exact_fields_fail_closed(
    tmp_path: Path, mutation: str
) -> None:
    a0, a0_root, decision, _ = _write_stage_a_inputs(tmp_path)
    a0_payload = json.loads((a0 / "report.json").read_text(encoding="utf-8"))
    decision_payload = json.loads(
        (decision / "decision.json").read_text(encoding="utf-8")
    )
    if mutation == "delete":
        decision_payload.pop("outcome_fields_consumed")
    elif mutation == "substitute_head":
        decision_payload["corrected_source_head"] = "b" * 40
    else:
        decision_payload["a0_root_sha256"] = "c" * 64
    with pytest.raises(ValueError, match="exact field/value contract"):
        builder.validate_a11_authority_payloads(
            a0_payload,
            decision_payload,
            a0_root_sha256=a0_root,
            current_head="a" * 40,
        )


@pytest.mark.parametrize("mutation", ["status", "formula", "nested", "progress"])
def test_a1_validator_rejects_semantic_and_fixture_mutations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    a0, a0_root, decision, decision_root = _write_stage_a_inputs(tmp_path)
    monkeypatch.setattr(builder, "_tracked_dirty", lambda _root: False)
    monkeypatch.setattr(builder, "_git_head", lambda _root: "a" * 40)
    monkeypatch.setattr(validator, "_tracked_dirty", lambda _root: False)
    monkeypatch.setattr(validator, "_git_head", lambda _root: "b" * 40)
    ledger, fixture = builder.build_ledger(
        a0_artifact=a0,
        a0_root_sha256=a0_root,
        ultra_decision_artifact=decision,
        ultra_decision_root_sha256=decision_root,
    )
    if mutation == "status":
        ledger["atoms"][0]["status"] = "OK"
    elif mutation == "formula":
        ledger["atoms"][0]["formula"] += "+silent-term"
    elif mutation == "nested":
        row = ledger["atoms"][0]
        row["dependencies"] = {"candidate": row.pop("k8_dependency")}
    else:
        fixture["progress_reference_adversarial"]["all_k_high_risk"][
            "source_valid_option"
        ]["status"] = "invalid_no_reference"
    artifact = tmp_path / f"ledger-{mutation}"
    root = _write_ledger_artifact(artifact, ledger, fixture)
    with pytest.raises(ValueError):
        validator.validate_ledger(
            ledger_artifact=artifact, ledger_root_sha256=root
        )
