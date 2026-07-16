from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
CONFIG = (
    ROOT
    / "configs"
    / "integrations"
    / "diffusion_planner_v24_convex_training_plan.json"
)


def _module():
    from scripts.integrations import (
        preflight_diffusion_planner_v24_convex_training,
    )

    return preflight_diffusion_planner_v24_convex_training


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _receipt_rows() -> list[dict]:
    rows = []
    index = 0
    for route_index in range(375):
        route = _sha(f"route:{route_index}")
        for seed in (24001, 24002, 24003, 24004, 24005):
            failed = index % 10 == 0
            rows.append(
                {
                    "phase": "pilot" if seed == 24001 else "remaining",
                    "relative_path": f"receipt:{route}:{seed}",
                    "sha256": _sha(f"receipt:{route}:{seed}"),
                    "record_key": f"record-{route_index}",
                    "map_family_id": "map-family-1",
                    "logical_map_sha256": _sha("logical-map"),
                    "corridor_group_sha256": _sha("corridor"),
                    "route_identity_sha256": route,
                    "seed": seed,
                    "status": "failed" if failed else "ok",
                    "snapshot_count": 37 if index < 296 else 36,
                    "failure_stage": "native_arm" if failed else None,
                    "failure_reason": "fixture failure" if failed else None,
                }
            )
            index += 1
    assert sum(row["snapshot_count"] for row in rows) == 67796
    return rows


def test_tracked_training_plan_freezes_label_curve_master_and_closed_boundaries() -> None:
    module = _module()
    normalized = module.validate_plan_config(_config())

    assert normalized["label_contract"]["physical_risk_penalty"] == 100.0
    assert normalized["label_contract"]["normalized_atom_clip"] == 10.0
    assert normalized["learning_curve_contract"]["levels_route_count"] == [
        94,
        188,
        281,
        375,
    ]
    assert normalized["convex_master_contract"]["solver"] == "CLARABEL"
    assert normalized["convex_master_contract"]["solver_fallback_allowed"] is False
    assert _config()["boundary_contract"]["training_execution_authorized"] is False
    assert _config()["boundary_contract"]["holdout_access_authorized"] is False


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("label_contract", "physical_risk_penalty", 99.0),
        ("label_contract", "scale_source", "recompute"),
        ("learning_curve_contract", "levels_route_count", [94, 188, 282, 375]),
        ("learning_curve_contract", "full_level_is_only_primary_model", False),
        ("convex_master_contract", "solver", "SCS"),
        ("convex_master_contract", "solver_status_required", "optimal_inaccurate"),
        ("convex_master_contract", "static_weight_lower_bounds", [0.01] * 14),
        ("convex_master_contract", "optimizer_initialization", "v22_weights"),
        ("boundary_contract", "training_execution_authorized", True),
        ("boundary_contract", "holdout_access_authorized", True),
    ],
)
def test_training_plan_drift_fails_closed(
    section: str, field: str, value: object
) -> None:
    module = _module()
    config = _config()
    config[section][field] = value

    with pytest.raises(ValueError):
        module.validate_plan_config(config)


def test_coordinated_source_authority_reseal_is_rejected_before_loading() -> None:
    module = _module()
    config = _config()
    for index, item in enumerate(config["source_authority"].values()):
        item["artifact"] = f"/root/autodl-tmp/coordinated_reseal_{index}"
        item["artifact_root_sha256"] = f"{index:x}" * 64

    with pytest.raises(ValueError, match="source authority"):
        module.validate_plan_config(config)


def test_route_prefix_is_nested_and_keeps_every_route_seed_and_failure() -> None:
    module = _module()
    routes, levels = module.build_route_prefix_plan(
        _receipt_rows(),
        namespace="camp-v24-learning-curve-route-order-v1",
    )

    assert len(routes) == 375
    assert [row["route_count"] for row in levels] == [94, 188, 281, 375]
    assert [row["retained_route_seed_count"] for row in levels] == [
        470,
        940,
        1405,
        1875,
    ]
    assert levels[-1]["snapshot_count"] == 67796
    assert levels[-1]["primary_model"] is True
    assert all(row["diagnostic_only"] for row in levels[:-1])
    assert all(row["seeds"] == [24001, 24002, 24003, 24004, 24005] for row in routes)
    assert all(
        row["complete_route_seed_count"] + row["failed_route_seed_count"] == 5
        for row in routes
    )


def test_route_prefix_is_invariant_to_receipt_input_order() -> None:
    module = _module()
    rows = _receipt_rows()
    expected_routes, expected_levels = module.build_route_prefix_plan(
        rows,
        namespace="camp-v24-learning-curve-route-order-v1",
    )
    random.Random(24).shuffle(rows)
    actual_routes, actual_levels = module.build_route_prefix_plan(
        rows,
        namespace="camp-v24-learning-curve-route-order-v1",
    )

    assert actual_routes == expected_routes
    assert actual_levels == expected_levels


def test_route_prefix_rejects_dropped_seed_duplicate_or_metadata_drift() -> None:
    module = _module()
    rows = _receipt_rows()
    with pytest.raises(ValueError, match="denominator"):
        module.build_route_prefix_plan(
            rows[:-1], namespace="camp-v24-learning-curve-route-order-v1"
        )

    duplicate = copy.deepcopy(rows)
    duplicate[-1]["route_identity_sha256"] = duplicate[0][
        "route_identity_sha256"
    ]
    duplicate[-1]["seed"] = duplicate[0]["seed"]
    duplicate[-1]["phase"] = duplicate[0]["phase"]
    with pytest.raises(ValueError, match="duplicate"):
        module.build_route_prefix_plan(
            duplicate, namespace="camp-v24-learning-curve-route-order-v1"
        )

    drift = copy.deepcopy(rows)
    drift[1]["logical_map_sha256"] = _sha("different-map")
    with pytest.raises(ValueError, match="metadata"):
        module.build_route_prefix_plan(
            drift, namespace="camp-v24-learning-curve-route-order-v1"
        )


def test_route_prefix_rejects_failed_receipt_without_cause() -> None:
    module = _module()
    rows = _receipt_rows()
    failed = next(row for row in rows if row["status"] == "failed")
    failed["failure_reason"] = None

    with pytest.raises(ValueError, match="lacks cause"):
        module.build_route_prefix_plan(
            rows, namespace="camp-v24-learning-curve-route-order-v1"
        )


@pytest.mark.parametrize("seed", [24001.0, True, np.int64(24001)])
def test_route_prefix_rejects_non_builtin_integer_seed(seed: object) -> None:
    module = _module()
    rows = _receipt_rows()
    rows[0]["seed"] = seed

    with pytest.raises(ValueError, match="invalid merged"):
        module.build_route_prefix_plan(
            rows, namespace="camp-v24-learning-curve-route-order-v1"
        )


def test_all_k_high_risk_keeps_finite_relative_cost_and_lowest_index_tie() -> None:
    module = _module()
    atoms = np.zeros((2, 8, 14), dtype=np.float64)
    atoms[0, :, 8] = np.arange(8, dtype=np.float64)
    valid = np.ones((2, 8), dtype=bool)
    physical = np.zeros((2, 8), dtype=bool)

    costs, oracle = module.causal_soft_risk_labels(
        atoms,
        source_valid=valid,
        physical_feasible=physical,
        frozen_scales=np.ones(14),
    )

    assert np.isfinite(costs).all()
    np.testing.assert_allclose(costs[0], 100.0 + 10.0 * np.arange(8))
    assert oracle.tolist() == [0, 0]


def test_causal_label_rejects_invalid_scale_and_source_empty_snapshot() -> None:
    module = _module()
    atoms = np.zeros((1, 8, 14), dtype=np.float64)
    valid = np.ones((1, 8), dtype=bool)
    physical = np.ones((1, 8), dtype=bool)
    bad_scales = np.ones(14)
    bad_scales[3] = 0.0
    with pytest.raises(ValueError):
        module.causal_soft_risk_labels(
            atoms,
            source_valid=valid,
            physical_feasible=physical,
            frozen_scales=bad_scales,
        )
    valid[:] = False
    with pytest.raises(ValueError):
        module.causal_soft_risk_labels(
            atoms,
            source_valid=valid,
            physical_feasible=physical,
            frozen_scales=np.ones(14),
        )


@pytest.mark.parametrize(
    "invalid_mask",
    [
        np.ones((1, 8), dtype=np.int64),
        np.ones((1, 8), dtype=np.float64),
        np.full((1, 8), "true", dtype="U4"),
    ],
)
def test_causal_label_rejects_non_boolean_masks(invalid_mask: np.ndarray) -> None:
    module = _module()
    atoms = np.zeros((1, 8, 14), dtype=np.float64)
    boolean_mask = np.ones((1, 8), dtype=bool)

    with pytest.raises(ValueError, match="must contain booleans"):
        module.causal_soft_risk_labels(
            atoms,
            source_valid=invalid_mask,
            physical_feasible=boolean_mask,
            frozen_scales=np.ones(14),
        )
    with pytest.raises(ValueError, match="must contain booleans"):
        module.causal_soft_risk_labels(
            atoms,
            source_valid=boolean_mask,
            physical_feasible=invalid_mask,
            frozen_scales=np.ones(14),
        )


def test_complete_seal_rejects_post_seal_nested_reserved_manifest(
    tmp_path: Path,
) -> None:
    module = _module()
    root = tmp_path / "artifact"
    root.mkdir()
    (root / "payload.txt").write_text("sealed\n", encoding="utf-8")
    digest = module.seal_artifact(root)
    assert module.verify_complete_seal(root, digest)

    nested = root / "nested"
    nested.mkdir()
    (nested / "SHA256SUMS").write_text("unsealed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="nested reserved"):
        module.verify_complete_seal(root, digest)


def test_sealer_rejects_preexisting_nested_reserved_manifest(tmp_path: Path) -> None:
    module = _module()
    root = tmp_path / "artifact"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (root / "payload.txt").write_text("sealed\n", encoding="utf-8")
    (nested / "ROOT_SHA256SUMS").write_text("forbidden\n", encoding="utf-8")

    with pytest.raises(ValueError, match="nested reserved"):
        module.seal_artifact(root)


def test_static_preflight_writes_route_plan_but_never_labels_or_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _module()
    merged = {
        "complete_route_seed_runs": 1687,
        "failed_route_seed_runs": 188,
        "all_k_high_risk_snapshot_count": 7783,
        "failure_reason_counts": {"fixture": 188},
    }
    freeze = {
        "atom_names": list(module.DP_CAMP_ATOM_NAMES_V10),
        "atom_scales": [1.0] * 14,
        "active_atom_mask": [True] * 14,
        "excluded_atom_names": [],
        "scale_rule": {"scope": "source_valid_train_candidates_only"},
        "variation_rule": {"scope": "within_tick_source_valid_candidates_only"},
    }
    monkeypatch.setattr(
        module, "verify_complete_seal", lambda _root, _sha: {"x": "y"}
    )
    monkeypatch.setattr(module, "_require_clean_execution_receipt", lambda _root: None)
    monkeypatch.setattr(
        module, "_validate_authority_payloads", lambda _roots, _digests: (merged, freeze)
    )
    monkeypatch.setattr(module, "_read_jsonl", lambda _path: _receipt_rows())
    monkeypatch.setitem(
        sys.modules,
        "cvxpy",
        SimpleNamespace(
            __version__="test-fixture",
            installed_solvers=lambda: ["CLARABEL"],
        ),
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    output = tmp_path / "preflight"

    result = module.run_static_preflight(
        repo=ROOT,
        dp_repo=tmp_path,
        config_path=CONFIG,
        expected_camp_head=head,
        output_dir=output,
        git_checker=lambda _repo, _head: None,
        dp_checker=lambda _repo: None,
        lock_checker=lambda: True,
        free_bytes=lambda: 20 * 1024**3,
        blob_bytes_reader=lambda repo, _head, relative: (
            repo / relative
        ).read_bytes(),
    )

    assert result["status"] == "passed"
    assert result["labels_materialized"] is False
    assert result["training_executed"] is False
    assert result["decision"]["training_execution_authorized"] is False
    assert result["decision"]["label_materialization_tdd_execution_authorized"] is True
    assert (output / "learning_curve_routes.jsonl").is_file()
    assert len((output / "learning_curve_routes.jsonl").read_text().splitlines()) == 375
    assert not (output / "labels").exists()
    assert not (output / "model.json").exists()
