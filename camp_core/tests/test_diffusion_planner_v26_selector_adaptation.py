from __future__ import annotations

import copy
import hashlib
import importlib
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_context import (
    PHI_DIMENSION,
    RAW_FEATURE_COUNT,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (
    training_parameter_array_sha256,
)
from camp_core.integrations.diffusion_planner_v26_integration_boundary import (
    V26_CERTIFIED_NO_SIGNAL_ADAPTER_ID,
    V26_CERTIFIED_NO_SIGNAL_MODE,
    V26SignalAdapterBinding,
    build_v26_integration_boundary,
    v26_generator_topology,
)
from camp_core.integrations.diffusion_planner_v26_development_profiling import (
    build_development_profiling_manifest,
)
from camp_core.integrations.diffusion_planner_v26_selector_adaptation import (
    ADAPTATION_MODEL_IDS,
    ADAPTATION_ROLE,
    SAVED_POOL_DIAGNOSTIC_ROLE,
    build_adaptation_manifest,
    build_adaptation_receipt,
    build_development_comparison_plan,
    build_saved_pool_selection_diagnostic,
    load_adaptation_config,
    load_train_only_saved_pools,
    load_zero_shot_reference_assets,
)


def _sha(index: int) -> str:
    return f"{index:064x}"


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _fixture_assets(tmp_path: Path) -> tuple[Path, Path]:
    count = 3
    training = tmp_path / "train_only"
    reference = tmp_path / "reference"
    training.mkdir()
    reference.mkdir()
    atoms = np.zeros((count, 8, 14), dtype=np.float64)
    atoms[0, 1, 0] = 1.0
    atoms[1, 2, 1] = 2.0
    atoms[2, 3, 2] = 3.0
    source = np.ones((count, 8), dtype=np.bool_)
    atom_source = np.ones((count, 8, 14), dtype=np.bool_)
    applicable = np.ones((count, 8, 14), dtype=np.bool_)
    physical = source.copy()
    physical[1, 7] = False
    raw_context = np.full((count, RAW_FEATURE_COUNT), 0.5, dtype=np.float64)
    context_source = np.ones((count, RAW_FEATURE_COUNT), dtype=np.bool_)
    oracle = np.asarray([0, 1, 2], dtype=np.int64)
    margins = np.tile(np.arange(8, dtype=np.float64), (count, 1))
    margins[1] = np.roll(margins[1], -1)
    margins[2] = np.roll(margins[2], -2)
    np.savez_compressed(
        training / "training_rows.npz",
        schema_version=np.asarray("camp_dp_v26_same_ego_b8_training_rows_v1"),
        normalized_atoms_14d=atoms,
        raw_context=raw_context,
        context_source_complete=context_source,
        oracle_indices=oracle,
        margins=margins,
        source_valid_mask=source,
        atom_source_valid_mask=atom_source,
        atom_applicable_mask=applicable,
        physical_feasible_mask=physical,
        record_weights=np.full(count, 1.0 / count, dtype=np.float64),
        route_ids=np.asarray(["route-a", "route-a", "route-b"]),
        semantic_block_ids=np.asarray(["block-a", "block-b", "block-c"]),
        corridor_ids=np.asarray(["corridor-a", "corridor-a", "corridor-b"]),
        map_family_ids=np.asarray(["map-a", "map-a", "map-b"]),
        family_tier=np.asarray(["f/t", "f/t", "f/t"]),
        seeds=np.asarray([11, 12, 13], dtype=np.int64),
        ticks=np.asarray([0, 1, 2], dtype=np.int64),
        scenario_ids=np.asarray(["scenario-a", "scenario-b", "scenario-c"]),
        source_manifest_sha256=np.asarray(_sha(900)),
        event_manifest_sha256=np.asarray([_sha(910), _sha(911), _sha(912)]),
        model_call_count=np.ones(count, dtype=np.int64),
        sequential_forward_count=np.zeros(count, dtype=np.int64),
        candidate0_row=np.zeros(count, dtype=np.int64),
        post_pool_model_dp_latent_generation_calls=np.zeros(count, dtype=np.int64),
        candidate_pool_mutation_count=np.zeros(count, dtype=np.int64),
        trajectory_regeneration_count=np.zeros(count, dtype=np.int64),
        latent_row_sha256=np.asarray(
            [[_sha(1000 + row * 8 + column) for column in range(8)] for row in range(count)]
        ),
        candidate_row_sha256=np.asarray(
            [[_sha(1100 + row * 8 + column) for column in range(8)] for row in range(count)]
        ),
        training_scales=np.ones(14, dtype=np.float64),
        severity=np.ones(14, dtype=np.float64),
    )
    rows_sha = hashlib.sha256((training / "training_rows.npz").read_bytes()).hexdigest()
    _write_json(
        training / "report.json",
        {
            "schema_version": "camp_dp_v26_same_ego_single_invocation_b8_training_source_v1",
            "evidence_role": "development_training_same_ego_b8_acquisition",
            "status": "terminal_training_evidence",
            "fixed_dp_head": "7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "generator_id": "fixed_dp_same_ego_single_invocation_b8_v1",
            "generator_topology": v26_generator_topology(),
            "outcome_fields_consumed": [],
            "holdout_accessed": False,
            "training_rows_schema_version": "camp_dp_v26_same_ego_b8_training_rows_v1",
            "training_rows_sha256": rows_sha,
            "source_manifest_sha256": _sha(900),
            "denominator": {"planned": count, "complete": count, "failed": 0, "unattempted": 0},
            "snapshot_count": count,
            "candidate_count": count * 8,
        },
    )
    _write_json(
        training / "label_sidecar.json",
        {
            "training_source_schema": "camp_dp_v26_same_ego_single_invocation_b8_training_source_v1",
            "label_contract": "causal_policy_distillation_no_outcome",
            "fresh_or_outcome_consumed": False,
            "identity_fields_used_as_label_or_feature": False,
        },
    )

    theta9 = np.full((9, PHI_DIMENSION), 1.0 / 9.0, dtype=np.float64)
    theta14 = np.full((14, PHI_DIMENSION), 1.0 / 14.0, dtype=np.float64)
    np.savez_compressed(
        reference / "model_parameters.npz",
        schema_version=np.asarray("camp_dp_v25_trained_model_parameters_v1"),
        context_q05=np.zeros(RAW_FEATURE_COUNT, dtype=np.float64),
        context_q95=np.ones(RAW_FEATURE_COUNT, dtype=np.float64),
        static9d_theta=theta9,
        scene9d_theta=theta9,
        static14d_theta=theta14,
        scene14d_theta=theta14,
    )
    parameters_sha = hashlib.sha256(
        (reference / "model_parameters.npz").read_bytes()
    ).hexdigest()
    _write_json(
        reference / "report.json",
        {
            "schema_version": "camp_dp_v25_strict_convex_training_artifact_v1",
            "status": "passed_strict_convex_training",
            "fixed_dp_head": "7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "outcome_fields_consumed": [],
            "fresh_b2_opened": False,
            "calibration_executed": False,
            "model_parameters_sha256": parameters_sha,
        },
    )
    _write_json(
        reference / "model_reports.json",
        {
            "CAMP-Static9D": {
                "theta_sha256": training_parameter_array_sha256(theta9),
                "outcome_or_fresh_consumed": False,
            },
            "CAMP-Scene9D": {
                "theta_sha256": training_parameter_array_sha256(theta9),
                "outcome_or_fresh_consumed": False,
            },
            "CAMP-Static14D": {
                "theta_sha256": training_parameter_array_sha256(theta14),
                "outcome_or_fresh_consumed": False,
            },
            "CAMP-Scene14D": {
                "theta_sha256": training_parameter_array_sha256(theta14),
                "outcome_or_fresh_consumed": False,
            },
        },
    )
    _write_json(reference / "runtime_atom_scales.json", {"scales": [1.0] * 14})
    return training, reference


def _adaptation_config_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "configs"
        / "integrations"
        / "diffusion_planner_v26_selector_adaptation_v1.json"
    )


def _profiling_manifest() -> dict[str, object]:
    return build_development_profiling_manifest(
        camp_head="a" * 40,
        probe_config_sha256=_sha(1),
        route_sha256=_sha(2),
        scenario_seed=17,
        spawn_config={"seed": 17},
        fixed_dp_head="7a1d33da277a1992ec474b5383a0c963c72e04e4",
        checkpoint_path="/fixed/model.pth",
        checkpoint_sha256=_sha(3),
        args_path="/fixed/args.json",
        args_sha256=_sha(4),
        reference_weights_root_sha256=_sha(5),
        reference_weights_review_root_sha256=_sha(6),
        atom_scales_sha256=_sha(7),
        static9d_weights_sha256=_sha(8),
        scene9d_theta_sha256=_sha(9),
        static14d_weights_sha256=_sha(10),
        scene14d_theta_sha256=_sha(11),
        context_scaler_sha256=_sha(12),
        integration_boundary=build_v26_integration_boundary(
            signal=V26SignalAdapterBinding(
                mode=V26_CERTIFIED_NO_SIGNAL_MODE,
                adapter_id=V26_CERTIFIED_NO_SIGNAL_ADAPTER_ID,
                adapter=object(),
                receipt={"fixture": True},
            ),
            reference_weights_root_sha256=_sha(5),
        ),
    )


def test_train_only_saved_pool_diagnostic_has_b8_identity_and_no_outcome_claims(
    tmp_path: Path,
) -> None:
    training, reference_dir = _fixture_assets(tmp_path)
    pools = load_train_only_saved_pools(training)
    reference = load_zero_shot_reference_assets(reference_dir)
    receipt = build_saved_pool_selection_diagnostic(pools, reference)

    assert receipt["evidence_role"] == SAVED_POOL_DIAGNOSTIC_ROLE
    assert receipt["denominator"] == {
        "planned": 3,
        "complete": 3,
        "failed": 0,
        "unattempted": 0,
    }
    assert receipt["source_pool_provenance"]["same_ego_batch_size"] == 8
    assert receipt["source_pool_provenance"]["stage7_model_dp_latent_generation_calls"] == 0
    assert set(receipt["selection_description"]["arms"]) == {
        "candidate0",
        *ADAPTATION_MODEL_IDS,
    }
    rendered = json.dumps(receipt, sort_keys=True)
    assert "support_status" not in rendered
    assert "ood_status" not in rendered
    assert "stability_status" not in rendered


def test_train_only_data_rejects_outcome_contamination(tmp_path: Path) -> None:
    training, _reference = _fixture_assets(tmp_path)
    report_path = training / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["outcome_fields_consumed"] = ["forbidden"]
    _write_json(report_path, report)

    with pytest.raises(ValueError, match="same-ego B8"):
        load_train_only_saved_pools(training)


def test_v26_fit_loader_rejects_a_v25_training_source_even_when_it_has_b8_rows(
    tmp_path: Path,
) -> None:
    training, _reference = _fixture_assets(tmp_path)
    report_path = training / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["schema_version"] = "camp_dp_v25_train_only_atom_audit_artifact_v1"
    _write_json(report_path, report)

    with pytest.raises(ValueError, match="reference-only"):
        load_train_only_saved_pools(training)


def test_zero_shot_loader_preserves_existing_simplex_tolerance_bytes(
    tmp_path: Path,
) -> None:
    _training, reference = _fixture_assets(tmp_path)
    parameter_path = reference / "model_parameters.npz"
    with np.load(parameter_path, allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    moved_mass = arrays["static14d_theta"][0, 0] + 1e-10
    arrays["static14d_theta"][0, 0] = -1e-10
    arrays["static14d_theta"][1, 0] += moved_mass
    np.savez_compressed(parameter_path, **arrays)
    report = json.loads((reference / "report.json").read_text(encoding="utf-8"))
    report["model_parameters_sha256"] = hashlib.sha256(parameter_path.read_bytes()).hexdigest()
    _write_json(reference / "report.json", report)
    model_reports = json.loads((reference / "model_reports.json").read_text(encoding="utf-8"))
    model_reports["CAMP-Static14D"]["theta_sha256"] = training_parameter_array_sha256(
        arrays["static14d_theta"]
    )
    _write_json(reference / "model_reports.json", model_reports)

    loaded = load_zero_shot_reference_assets(reference)

    assert loaded.static14d_theta[0, 0] == pytest.approx(-1e-10)


def test_adaptation_config_and_receipt_bind_selector_only_scope(tmp_path: Path) -> None:
    training, reference_dir = _fixture_assets(tmp_path)
    config = load_adaptation_config(_adaptation_config_path())
    pools = load_train_only_saved_pools(training)
    reference = load_zero_shot_reference_assets(reference_dir)
    with pytest.raises(ValueError, match="final population receipt"):
        build_adaptation_manifest(
            camp_head="b" * 40,
            config=config,
            data=pools,
            reference=reference,
            fixed_dp_checkpoint={"path": "/fixed/model.pth", "sha256": _sha(21)},
            fixed_dp_args={"path": "/fixed/args.json", "sha256": _sha(22)},
        )

    payload = copy.deepcopy(config.payload)
    payload["frozen_components"].pop()
    bad_config = tmp_path / "bad.json"
    _write_json(bad_config, payload)
    with pytest.raises(ValueError, match="identity"):
        load_adaptation_config(bad_config)


def test_comparison_plan_prefixes_new_nonholdout_identities_without_profiles() -> None:
    manifest = _profiling_manifest()
    plan = build_development_comparison_plan(
        manifest, profiling_manifest_sha256=_sha(31)
    )
    assert plan["status"] == "prepared_no_execution_no_claim"
    assert plan["state_count"] == 20
    assert plan["disjoint_from_profiling"]["scenario_seed_differs"] is True
    assert plan["disjoint_from_profiling"]["same_pool_profiling_reuse_forbidden"] is True
    assert plan["arms"][:5] == [
        "candidate0",
        "Static9D_zero_shot",
        "Scene9D_zero_shot",
        "Static14D_zero_shot",
        "Scene14D_zero_shot",
    ]


def test_stage7_parsers_accept_only_direct_training_and_planning_inputs() -> None:
    diagnostic = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_saved_pool_selection_diagnostic"
    )
    trainer = importlib.import_module(
        "scripts.integrations.train_diffusion_planner_v26_selector_adaptation"
    )
    planner = importlib.import_module(
        "scripts.integrations.plan_diffusion_planner_v26_development_comparison"
    )
    parsed = diagnostic.parse_args(
        [
            "--output-dir",
            "diagnostic",
            "--training-source",
            "training",
            "--reference-training",
            "reference",
        ]
    )
    assert parsed.output_dir == Path("diagnostic")
    train_args = trainer.parse_args(
        [
            "--output-dir",
            "output",
            "--worker-lock",
            "lock",
            "--training-source",
            "training",
            "--final-population-receipt",
            "population-receipt.json",
            "--reference-training",
            "reference",
            "--config",
            "config.json",
            "--fixed-dp-repo",
            "fixed-dp",
            "--fixed-dp-checkpoint",
            "checkpoint",
            "--fixed-dp-checkpoint-sha256",
            _sha(41),
            "--fixed-dp-args",
            "args",
            "--fixed-dp-args-sha256",
            _sha(42),
        ]
    )
    assert train_args.fixed_dp_repo == Path("fixed-dp")
    assert train_args.final_population_receipt == Path("population-receipt.json")
    plan_args = planner.parse_args(
        ["--profiling-manifest", "manifest.json", "--output", "plan.json"]
    )
    assert plan_args.output == Path("plan.json")
    with pytest.raises(SystemExit):
        diagnostic.parse_args(
            [
                "--output-dir",
                "diagnostic",
                "--training-source",
                "training",
                "--reference-training",
                "reference",
                "--evaluate-all",
            ]
        )
