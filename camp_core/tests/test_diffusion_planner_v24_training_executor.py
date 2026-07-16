from __future__ import annotations

import ast
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
EXECUTOR = ROOT / "scripts" / "integrations" / "train_diffusion_planner_v24_selector.py"


def _module():
    from scripts.integrations import train_diffusion_planner_v24_selector

    return train_diffusion_planner_v24_selector


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _config(module):
    from camp_core.outer_master.robust_margin_master import RobustMarginConfig

    return RobustMarginConfig(
        mode="static",
        risk_type="cvar",
        alpha=module.CVAR_ALPHA,
        l2_reg=module.L2_REGULARIZATION,
        max_iter=module.MAX_ITERATIONS,
        tolerance=module.ACCEPTANCE_GAP,
        solver=module.SOLVER,
        static_weight_lower_bounds=tuple([0.0] * 14),
        solver_options=module.SOLVER_OPTIONS,
    )


def _problem(rows: int = 3):
    atoms = np.zeros((rows, 8, 14), dtype=np.float64)
    atoms[:, :, 0] = np.arange(8, dtype=np.float64)
    costs = np.broadcast_to(np.arange(8, dtype=np.float64), (rows, 8)).copy()
    valid = np.ones((rows, 8), dtype=bool)
    oracle = np.zeros(rows, dtype=np.uint8)
    return atoms, costs, valid, oracle


def _result(module, rows: int = 3):
    weights = np.full(14, 1.0 / 14.0, dtype=np.float64)
    cuts = np.zeros((rows, 8), dtype=bool)
    cuts[:, 0] = True
    return module.V24CuttingPlaneResult(
        raw_static_weights=weights,
        train_violations=np.zeros(rows, dtype=np.float64),
        final_master_gap=0.0,
        projected_train_violations=np.zeros(rows, dtype=np.float64),
        final_projected_master_gap=0.0,
        final_raw_cut_gap=0.0,
        final_projected_cut_gap=0.0,
        history=[
            {
                "iteration": 1,
                "master_objective": 0.0,
                "exact_cvar": 0.0,
                "mean_violation": 0.0,
                "max_violation": 0.0,
                "max_master_gap": 0.0,
                "raw_max_cut_gap": 0.0,
                "projected_max_cut_gap": 0.0,
                "max_separation_gap": 0.0,
                "new_cuts": 0,
                "total_cuts": rows,
                "final_resolve": False,
            }
        ],
        converged=True,
        final_cut_mask=cuts,
        final_master_losses=np.zeros(rows, dtype=np.float64),
        solver_status="optimal",
        solver_name="CLARABEL",
        registry_receipt={
            "installed_solvers_before_scope": ["CLARABEL", "SCS"],
            "solvers_exposed_to_master": ["CLARABEL"],
            "fallback_solvers_exposed": [],
        },
    )


def test_training_problem_uses_source_valid_oracle_and_frozen_margin() -> None:
    module = _module()
    atoms, costs, valid, oracle = _problem(2)
    valid[0, 0] = False
    oracle[0] = 1

    problem = module.prepare_training_problem(
        atoms, costs, valid, oracle, frozen_scales=np.ones(14)
    )

    assert problem["oracle_indices"].tolist() == [1, 0]
    assert problem["margins"][0, 0] == 0.0
    np.testing.assert_allclose(problem["margins"][1], np.arange(8) * 0.1)
    np.testing.assert_allclose(problem["normalized_atoms"], np.clip(atoms, 0, 10))


def test_training_problem_rejects_oracle_mask_scale_and_nonfinite_drift() -> None:
    module = _module()
    atoms, costs, valid, oracle = _problem(1)
    cases = [
        (atoms, costs, valid.astype(np.uint8), oracle, np.ones(14)),
        (atoms, costs, valid, np.asarray([1], dtype=np.uint8), np.ones(14)),
        (atoms, costs, valid, oracle, np.zeros(14)),
        (atoms.copy(), costs, valid, oracle, np.ones(14)),
    ]
    cases[-1][0][0, 0, 0] = np.nan
    for matrix, values, mask, stored_oracle, scales in cases:
        with pytest.raises(ValueError):
            module.prepare_training_problem(
                matrix,
                values,
                mask,
                stored_oracle,
                frozen_scales=scales,
            )


@pytest.mark.parametrize("alpha", [0.0, 0.5, 0.9, 0.99])
def test_fast_empirical_cvar_exactly_matches_frozen_reference(alpha: float) -> None:
    module = _module()
    from camp_core.outer_master.robust_margin_master import empirical_cvar

    rng = np.random.default_rng(24038)
    losses = np.round(rng.normal(size=127), 1)
    actual = module.empirical_cvar_fast(losses, alpha)
    expected = empirical_cvar(losses, alpha)

    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-12)


def test_clarabel_registry_is_process_local_and_hides_fallbacks(monkeypatch) -> None:
    module = _module()
    fake = SimpleNamespace(installed_solvers=lambda: ["SCS", "CLARABEL", "OSQP"])
    original = fake.installed_solvers
    monkeypatch.setitem(sys.modules, "cvxpy", fake)

    with module.clarabel_only_solver_registry() as receipt:
        assert fake.installed_solvers() == ["CLARABEL"]
        assert receipt["solvers_exposed_to_master"] == ["CLARABEL"]
        assert receipt["fallback_solvers_exposed"] == []

    assert fake.installed_solvers is original
    assert fake.installed_solvers() == ["SCS", "CLARABEL", "OSQP"]


def test_cutting_plane_has_one_clarabel_call_and_no_fallback_retry() -> None:
    module = _module()
    atoms, costs, valid, oracle = _problem(2)
    problem = module.prepare_training_problem(
        atoms, costs, valid, oracle, frozen_scales=np.ones(14)
    )
    calls = []

    @contextmanager
    def scope():
        yield {
            "installed_solvers_before_scope": ["CLARABEL", "SCS"],
            "solvers_exposed_to_master": ["CLARABEL"],
            "fallback_solvers_exposed": [],
        }

    def master(*args):
        calls.append(args)
        weights = np.full(14, 1.0 / 14.0)
        _, true_losses, _ = module.candidate_ranking_violations(
            args[0], weights, args[1], args[2], valid
        )
        return weights, None, true_losses, "optimal", "CLARABEL", 0.0

    result = module.solve_v24_cutting_plane(
        problem["normalized_atoms"],
        problem["oracle_indices"],
        problem["margins"],
        problem["source_valid_mask"],
        config=_config(module),
        master_solver=master,
        solver_scope=scope,
    )

    assert len(calls) == 1
    assert result.history[-1]["new_cuts"] == 0
    assert result.history[-1]["final_resolve"] is False
    assert len(result.history) <= 20

    calls.clear()

    def fail_once(*args):
        calls.append(args)
        raise RuntimeError("CLARABEL SolverError")

    with pytest.raises(RuntimeError, match="SolverError"):
        module.solve_v24_cutting_plane(
            problem["normalized_atoms"],
            problem["oracle_indices"],
            problem["margins"],
            problem["source_valid_mask"],
            config=_config(module),
            master_solver=fail_once,
            solver_scope=scope,
        )
    assert len(calls) == 1


def test_cutting_plane_adds_projected_weight_violation_before_convergence() -> None:
    module = _module()
    atoms = np.zeros((1, 8, 14), dtype=np.float64)
    atoms[0, 0, 1:] = 10.0
    atoms[0, 1, 1:] = 9.0
    atoms[0, 2, 0] = 10.0
    valid = np.ones((1, 8), dtype=bool)
    oracle = np.asarray([0], dtype=np.int64)
    margins = np.zeros((1, 8), dtype=np.float64)
    margins[0, 1] = 1.1e-6
    raw = np.asarray([1.0 + 13e-8] + [-1e-8] * 13, dtype=np.float64)
    projected = np.asarray([1.0] + [0.0] * 13, dtype=np.float64)
    calls = []

    @contextmanager
    def scope():
        yield {
            "installed_solvers_before_scope": ["CLARABEL"],
            "solvers_exposed_to_master": ["CLARABEL"],
            "fallback_solvers_exposed": [],
        }

    def master(atoms_arg, oracle_arg, margins_arg, cuts, config, features):
        calls.append([set(row) for row in cuts])
        weights = raw if len(calls) == 1 else projected
        _, losses, _ = module.candidate_ranking_violations(
            atoms_arg, weights, oracle_arg, margins_arg, valid
        )
        master_losses = np.zeros(1) if len(calls) == 1 else losses
        return weights, None, master_losses, "optimal", "CLARABEL", 0.0

    result = module.solve_v24_cutting_plane(
        atoms,
        oracle,
        margins,
        valid,
        config=_config(module),
        master_solver=master,
        solver_scope=scope,
    )

    assert len(calls) == 2
    assert 1 not in calls[0][0]
    assert 1 in calls[1][0]
    assert result.history[0]["raw_max_master_gap"] <= module.ACCEPTANCE_GAP
    assert result.history[0]["projected_max_master_gap"] > module.ACCEPTANCE_GAP
    assert result.history[-1]["new_cuts"] == 0
    assert result.final_master_gap <= module.ACCEPTANCE_GAP
    assert result.final_projected_master_gap <= module.ACCEPTANCE_GAP


def test_cutting_plane_adds_cut_relative_violation_when_master_gap_passes() -> None:
    module = _module()
    atoms = np.zeros((1, 8, 14), dtype=np.float64)
    atoms[0, 0, 1:] = 10.0
    atoms[0, 1, 1:] = 9.0
    atoms[0, 2, 0] = 10.0
    valid = np.ones((1, 8), dtype=bool)
    oracle = np.asarray([0], dtype=np.int64)
    margins = np.zeros((1, 8), dtype=np.float64)
    margins[0, 1] = 1.1e-6
    raw = np.asarray([1.0 + 13e-8] + [-1e-8] * 13, dtype=np.float64)
    projected = np.asarray([1.0] + [0.0] * 13, dtype=np.float64)
    calls = []

    @contextmanager
    def scope():
        yield {
            "installed_solvers_before_scope": ["CLARABEL"],
            "solvers_exposed_to_master": ["CLARABEL"],
            "fallback_solvers_exposed": [],
        }

    def master(atoms_arg, oracle_arg, margins_arg, cuts, config, features):
        calls.append([set(row) for row in cuts])
        weights = raw if len(calls) == 1 else projected
        projected_losses = module.candidate_ranking_violations(
            atoms_arg, projected, oracle_arg, margins_arg, valid
        )[1]
        return weights, None, projected_losses, "optimal", "CLARABEL", 0.0

    result = module.solve_v24_cutting_plane(
        atoms,
        oracle,
        margins,
        valid,
        config=_config(module),
        master_solver=master,
        solver_scope=scope,
    )

    assert len(calls) == 2
    assert 1 not in calls[0][0]
    assert 1 in calls[1][0]
    assert result.history[0]["projected_max_master_gap"] <= module.ACCEPTANCE_GAP
    assert result.history[0]["projected_max_cut_gap"] > module.ACCEPTANCE_GAP
    assert result.history[-1]["new_cuts"] == 0
    assert result.final_raw_cut_gap <= module.ACCEPTANCE_GAP
    assert result.final_projected_cut_gap <= module.ACCEPTANCE_GAP


def test_saved_weight_acceptance_recomputes_full_k_and_rejects_final_resolve() -> None:
    module = _module()
    rows = 3
    atoms = np.zeros((rows, 8, 14), dtype=np.float64)
    oracle = np.zeros(rows, dtype=np.int64)
    margins = np.zeros((rows, 8), dtype=np.float64)
    feasible = np.ones((rows, 8), dtype=bool)
    result = _result(module, rows)

    weights, losses, gap, receipt = module.accepted_weights_and_gap(
        result, atoms, oracle, margins, feasible
    )

    np.testing.assert_allclose(weights, np.full(14, 1.0 / 14.0))
    np.testing.assert_array_equal(losses, np.zeros(rows))
    assert gap == 0.0
    assert receipt["omitted_violating_snapshot_count"] == 0

    result.history[-1]["final_resolve"] = True
    with pytest.raises(RuntimeError, match="final-resolve"):
        module.accepted_weights_and_gap(result, atoms, oracle, margins, feasible)


def test_saved_weight_acceptance_rejects_omitted_full_k_violation() -> None:
    module = _module()
    result = _result(module, 1)
    atoms = np.zeros((1, 8, 14), dtype=np.float64)
    atoms[0, 1, 0] = -1.0
    oracle = np.zeros(1, dtype=np.int64)
    margins = np.zeros((1, 8), dtype=np.float64)
    feasible = np.ones((1, 8), dtype=bool)

    with pytest.raises(RuntimeError, match="full-K"):
        module.accepted_weights_and_gap(result, atoms, oracle, margins, feasible)


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("final_raw_cut_gap", "raw full-K cut gap"),
        ("final_projected_cut_gap", "projected full-K cut gap"),
    ],
)
def test_saved_weight_acceptance_requires_both_reported_cut_gaps(
    field: str, message: str
) -> None:
    module = _module()
    result = _result(module, 1)
    setattr(result, field, 2.0 * module.ACCEPTANCE_GAP)
    atoms = np.zeros((1, 8, 14), dtype=np.float64)
    oracle = np.zeros(1, dtype=np.int64)
    margins = np.zeros((1, 8), dtype=np.float64)
    feasible = np.ones((1, 8), dtype=bool)

    with pytest.raises(RuntimeError, match=message):
        module.accepted_weights_and_gap(result, atoms, oracle, margins, feasible)


def test_route_rows_freeze_all_seeds_failures_and_nested_membership() -> None:
    module = _module()
    routes = []
    for rank in range(1, 376):
        routes.append(
            {
                "route_identity_sha256": _sha(f"route:{rank}"),
                "route_order_key_sha256": _sha(f"order:{rank}"),
                "map_family_id": "family",
                "logical_map_sha256": _sha("map"),
                "corridor_group_sha256": _sha("corridor"),
                "seeds": list(module.EXPECTED_SEEDS),
                "retained_route_seed_count": 5,
                "complete_route_seed_count": 4,
                "failed_route_seed_count": 1,
                "snapshot_count": 1,
                "route_order_rank": rank,
                "included_learning_curve_percent": [
                    percent
                    for percent, count in zip(
                        module.EXPECTED_LEVELS, module.EXPECTED_LEVEL_ROUTES
                    )
                    if rank <= count
                ],
            }
        )

    route_ids, route_by_id = module._validate_route_rows(routes)

    assert len(route_ids) == 375
    assert set(route_by_id) == route_ids
    routes[0]["seeds"] = list(module.EXPECTED_SEEDS[:-1])
    with pytest.raises(ValueError, match="provenance"):
        module._validate_route_rows(routes)


@pytest.mark.parametrize(
    ("phase", "seed", "expected"),
    [
        ("pilot", 24001, True),
        ("remaining", 24002, True),
        ("remaining", 24005, True),
        ("remaining", 24001, False),
        ("pilot", 24002, False),
        ("train", 24001, False),
        ("pilot", np.int64(24001), False),
    ],
)
def test_provenance_phase_is_exactly_bound_to_pilot_and_remaining_seed_namespaces(
    phase: str, seed: object, expected: bool
) -> None:
    module = _module()
    assert module._valid_provenance_phase_seed(phase, seed) is expected


def test_label_payload_receipts_are_byte_and_schema_bound(
    tmp_path: Path, monkeypatch
) -> None:
    module = _module()
    filenames = {
        "snapshot_sha256.txt": b"x\n",
        "snapshot_provenance.jsonl": b"{}\n",
        "candidate_cost.f64le": b"cost",
        "oracle_index.u8": b"oracle",
        "source_valid_mask.u8": b"valid",
        "physical_feasible_mask.u8": b"physical",
        "all_k_high_risk.u8": b"risk",
    }
    for name, content in filenames.items():
        (tmp_path / name).write_bytes(content)
    monkeypatch.setattr(module, "LABEL_ARTIFACT", tmp_path)
    label = {
        "columns": {
            "candidate_cost": {
                "file": "candidate_cost.f64le",
                "dtype": "<f8",
                "shape": [module.EXPECTED_SNAPSHOTS, 8],
            },
            "oracle_index": {
                "file": "oracle_index.u8",
                "dtype": "u1",
                "shape": [module.EXPECTED_SNAPSHOTS],
            },
            "source_valid_mask": {
                "file": "source_valid_mask.u8",
                "dtype": "u1_bool",
                "shape": [module.EXPECTED_SNAPSHOTS, 8],
            },
            "physical_feasible_mask": {
                "file": "physical_feasible_mask.u8",
                "dtype": "u1_bool",
                "shape": [module.EXPECTED_SNAPSHOTS, 8],
            },
            "all_k_high_risk": {
                "file": "all_k_high_risk.u8",
                "dtype": "u1_bool",
                "shape": [module.EXPECTED_SNAPSHOTS],
            },
        },
        "file_receipts": {
            name: {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
            for name, content in filenames.items()
        },
    }

    module._verify_label_payload_receipts(label)
    label["file_receipts"]["oracle_index.u8"]["bytes"] += 1
    with pytest.raises(ValueError, match="receipt"):
        module._verify_label_payload_receipts(label)


def test_model_writer_keeps_cut_mask_and_weights_as_sealed_binary_receipts(
    tmp_path: Path,
) -> None:
    module = _module()
    model = {
        "schema": "camp_dp_v24_static_affine_selector_model_v1",
        "weights": [1.0] + [0.0] * 13,
        "_final_cut_mask": np.ones((2, 8), dtype=bool),
    }
    result = {"models": {str(level): dict(model) for level in module.EXPECTED_LEVELS}}

    output = tmp_path / "training"
    module.write_training_outputs(result, output)
    manifest = json.loads((output / "training_manifest.json").read_text())

    assert set(manifest["model_receipts"]) == {"25", "50", "75", "100"}
    assert manifest["primary_model_receipt"] == manifest["model_receipts"]["100"]
    assert (output / "models/level_100_weights.f64le").stat().st_size == 14 * 8
    assert (output / "models/level_100_final_cut_mask.u8").read_bytes() == b"\x01" * 16
    model_payload = json.loads((output / "models/level_100.json").read_text())
    assert "_final_cut_mask" not in model_payload
    assert model_payload["final_cut_mask"]["path"].endswith(
        "level_100_final_cut_mask.u8"
    )


def test_learning_curve_solves_four_fresh_levels_and_emits_progress(monkeypatch) -> None:
    module = _module()
    atoms = np.zeros((4, 8, 14), dtype=np.float64)
    inputs = {
        "levels": [
            {
                "percent": level,
                "route_membership_sha256": _sha(str(level)),
                "route_count": 1,
                "retained_route_seed_count": 5,
                "complete_route_seed_count": 5,
                "failed_route_seed_count": 0,
            }
            for level in module.EXPECTED_LEVELS
        ],
        "level_indices": {level: np.asarray([index]) for index, level in enumerate(module.EXPECTED_LEVELS)},
        "atoms": atoms,
        "candidate_cost": np.zeros((4, 8), dtype=np.float64),
        "source_valid_mask": np.ones((4, 8), dtype=bool),
        "physical_feasible_mask": np.ones((4, 8), dtype=bool),
        "all_k_high_risk": np.zeros(4, dtype=bool),
        "oracle_index": np.zeros(4, dtype=np.uint8),
        "atom_scales": np.ones(14),
        "snapshot_sha256": [_sha(f"snapshot:{index}") for index in range(4)],
        "failure_reason_counts": {},
        "source_verified_file_counts": {},
        "direct_source_verified_file_counts": {},
    }
    calls = []

    def fake_train_level(**kwargs):
        calls.append(kwargs["level_percent"])
        return {
            "solver": {"iterations": 1, "offline_wall_clock_s": 0.01},
            "_final_cut_mask": np.ones((1, 8), dtype=bool),
            "weights": [1.0] + [0.0] * 13,
        }

    monkeypatch.setattr(module, "train_level", fake_train_level)
    progress = []
    result = module.train_learning_curve(inputs, progress_callback=progress.append)

    assert calls == [25, 50, 75, 100]
    assert list(result["models"]) == ["25", "50", "75", "100"]
    assert [row["phase"] for row in progress] == [
        "level_started",
        "level_completed",
    ] * 4
    assert progress[-1]["completed_levels"] == ["25", "50", "75", "100"]


def test_progress_receipt_is_atomic_and_marks_terminal_state(tmp_path: Path) -> None:
    module = _module()
    module._write_progress(
        tmp_path,
        {"phase": "level_started", "level_percent": 25, "completed_levels": []},
    )
    active = json.loads((tmp_path / "progress.json").read_text())
    assert active["training_execution_active"] is True
    assert not (tmp_path / "progress.json.tmp").exists()

    module._write_progress(
        tmp_path,
        {"phase": "training_completed", "completed_levels": ["25", "50", "75", "100"]},
    )
    completed = json.loads((tmp_path / "progress.json").read_text())
    assert completed["training_execution_active"] is False


def test_executor_source_has_no_outcome_weight_reuse_or_model_selection_path() -> None:
    source = EXECUTOR.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert "pickle" not in imported
    assert "torch" not in imported
    assert "load" not in calls
    historical_weight_strings = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and ("v18" in node.value.lower() or "v22" in node.value.lower())
    }
    assert historical_weight_strings == {"v18_v22_weights_loaded"}
    assert '"curve_models_used_for_model_selection": False' in source
    assert '"identity_fields_used_as_feature": False' in source
    assert '"actual_closed_loop_outcomes_read": False' in source


def test_independent_static_reviewer_accepts_executor_and_rejects_contract_drift() -> None:
    from scripts.integrations import (
        review_diffusion_planner_v24_training_executor_preflight as reviewer,
    )

    source = EXECUTOR.read_text(encoding="utf-8")
    checks = reviewer._static_executor_review(source)

    assert "clarabel_only_registry" in checks
    assert "no_post_cap_final_resolve" in checks
    assert "saved_weights_recomputed_full_k" in checks
    assert "raw_and_projected_cut_relative_separation" in checks
    assert "all_four_gap_acceptance" in checks
    with pytest.raises(ValueError, match="static contract"):
        reviewer._static_executor_review(
            source.replace('"final_resolve": False', '"final_resolve": True', 1)
        )
    with pytest.raises(ValueError, match="static contract"):
        reviewer._static_executor_review(
            source.replace(
                "v24_convex_selector_training_cut_relative_gap_retry_execution_only",
                "v24_convex_selector_training_retry_execution_only",
                1,
            )
        )


def test_training_execution_authorization_binds_cut_relative_review(
    tmp_path: Path, monkeypatch
) -> None:
    module = _module()
    audit = tmp_path / "docs" / "diffusion_planner_v24_iteration_audit.md"
    audit.parent.mkdir()
    artifact = Path("/root/autodl-tmp/cut-relative-review")
    root = "a" * 64
    camp_head = "b" * 40
    executor_path = tmp_path / module.EXECUTOR_PROVENANCE_FILES[0]
    executor_path.parent.mkdir(parents=True)
    executor_path.write_bytes(b"current executor")
    pointer = [
        "current_v24_status=v24_convex_training_cut_relative_gap_authorization_contract_repair_static_preflight_independent_review_passed",
        f"current_v24_artifact_source_head={camp_head}",
        f"current_v24_artifact={artifact}",
        f"current_v24_artifact_root_sha256={root}",
        "next_work_target=v24_convex_selector_training_cut_relative_gap_retry_execution_only",
    ]
    audit.write_text("\n".join(["header"] * 10 + pointer) + "\n", encoding="utf-8")
    review = {
        "schema": (
            "camp_dp_v24_training_cut_relative_gap_authorization_contract_"
            "repair_static_preflight_"
            "independent_review_v1"
        ),
        "status": "passed",
        "camp_head": camp_head,
        "executor_source_sha256": hashlib.sha256(b"current executor").hexdigest(),
        "decision": {
            "training_execution_authorized": True,
            "training_retry_authorized": True,
        },
        "outcome_accessed": False,
        "calibration_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
    }
    monkeypatch.setattr(module, "verify_complete_seal", lambda *_args: [])
    monkeypatch.setattr(module, "_read_json", lambda _path: review)

    assert module._authorization_from_eof(
        repo=tmp_path,
        artifact=artifact,
        expected_root=root,
        expected_camp_head=camp_head,
    ) == review
    review["executor_source_sha256"] = "c" * 64
    with pytest.raises(ValueError, match="does not authorize"):
        module._authorization_from_eof(
            repo=tmp_path,
            artifact=artifact,
            expected_root=root,
            expected_camp_head=camp_head,
        )
    review["executor_source_sha256"] = hashlib.sha256(b"current executor").hexdigest()
    audit.write_text(
        audit.read_text(encoding="utf-8").replace(
            "v24_convex_training_cut_relative_gap_authorization_contract_"
            "repair_static_preflight_"
            "independent_review_passed",
            "v24_convex_training_projection_boundary_repair_static_preflight_"
            "independent_review_passed",
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="does not authorize"):
        module._authorization_from_eof(
            repo=tmp_path,
            artifact=artifact,
            expected_root=root,
            expected_camp_head=camp_head,
        )


def test_execution_provenance_binds_executor_preflight_reviewer_and_frozen_core() -> None:
    module = _module()
    from scripts.integrations import (
        review_diffusion_planner_v24_training_executor_preflight as reviewer,
    )

    assert set(module.EXECUTOR_PROVENANCE_FILES) == {
        "scripts/integrations/train_diffusion_planner_v24_selector.py",
        "scripts/integrations/preflight_diffusion_planner_v24_training_executor.py",
        "scripts/integrations/review_diffusion_planner_v24_training_executor_preflight.py",
        "scripts/integrations/review_diffusion_planner_v24_training_execution_failure.py",
        "scripts/integrations/review_diffusion_planner_v24_training_retry_failure.py",
        "configs/integrations/diffusion_planner_v24_convex_training_plan.json",
        "camp_core/camp_core/outer_master/robust_margin_master.py",
        "scripts/integrations/preflight_diffusion_planner_v24_convex_training.py",
        "scripts/integrations/review_diffusion_planner_v24_atom_availability.py",
    }
    assert set(module.PLAN_STABLE_PROVENANCE_FILES) == {
        "configs/integrations/diffusion_planner_v24_convex_training_plan.json",
        "camp_core/camp_core/outer_master/robust_margin_master.py",
        "scripts/integrations/preflight_diffusion_planner_v24_convex_training.py",
        "scripts/integrations/review_diffusion_planner_v24_atom_availability.py",
    }
    assert set(reviewer.EXPECTED_PROVENANCE) == set(module.EXECUTOR_PROVENANCE_FILES)
    assert set(reviewer.PLAN_STABLE) == set(module.PLAN_STABLE_PROVENANCE_FILES)


def test_static_test_artifact_receipt_binds_files_count_and_closed_boundaries(
    tmp_path: Path, monkeypatch
) -> None:
    from scripts.integrations import (
        preflight_diffusion_planner_v24_training_executor as preflight,
    )

    (tmp_path / "run.exit").write_text("0\n", encoding="ascii")
    (tmp_path / "stderr.txt").write_text("", encoding="utf-8")
    (tmp_path / "stdout.txt").write_text("18 passed in 1.00s\n", encoding="utf-8")
    receipt = {
        "schema": preflight.TEST_SCHEMA,
        "status": "passed",
        "camp_head": "a" * 40,
        "fixed_dp_head": preflight.FIXED_DP_HEAD,
        "required_test_files": list(preflight.REQUIRED_TEST_FILES),
        "passed_count": 18,
        "training_executed": False,
        "corpus_solver_called": False,
        "calibration_accessed": False,
        "holdout_opened": False,
    }
    (tmp_path / "test_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    monkeypatch.setattr(preflight, "_safe_autodl_artifact", lambda _path: None)
    monkeypatch.setattr(preflight, "verify_complete_seal", lambda _path, _root: [1, 2])

    verified = preflight.verify_static_test_artifact(
        root=tmp_path, expected_root_sha256="b" * 64, camp_head="a" * 40
    )

    assert verified["verified_file_count"] == 2
    receipt["training_executed"] = True
    (tmp_path / "test_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="receipt drift"):
        preflight.verify_static_test_artifact(
            root=tmp_path, expected_root_sha256="b" * 64, camp_head="a" * 40
        )


def test_first_training_failure_has_independent_projection_boundary_diagnosis() -> None:
    from scripts.integrations import (
        review_diffusion_planner_v24_training_execution_failure as reviewer,
    )

    source = subprocess.run(
        [
            "git",
            "show",
            f"{reviewer.FAILURE_CAMP_HEAD}:{reviewer.EXECUTOR_RELATIVE}",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    diagnosis = reviewer.diagnose_projection_boundary(source)

    assert diagnosis["cut_generation_uses_raw_weights"] is True
    assert diagnosis["cut_generation_projects_weights"] is False
    assert diagnosis["acceptance_projects_weights"] is True
    assert diagnosis["acceptance_rejects_projected_gap"] is True


def test_training_retry_failure_distinguishes_master_and_cut_relative_gap() -> None:
    from scripts.integrations import (
        review_diffusion_planner_v24_training_retry_failure as reviewer,
    )

    source = subprocess.run(
        [
            "git",
            "show",
            f"{reviewer.RETRY_CAMP_HEAD}:{reviewer.EXECUTOR_RELATIVE}",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    diagnosis = reviewer.diagnose_master_vs_cut_gap(source)

    assert diagnosis["projected_cut_separation_present"] is True
    assert diagnosis["projected_gap_is_relative_to_master_losses"] is True
    assert diagnosis["cut_relative_gap_computed_during_separation"] is False
    assert diagnosis["cut_relative_gap_required_during_acceptance"] is True
