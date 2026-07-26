from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations import (
    diffusion_planner_v25_industrial_evaluation_contract_v2 as v2,
)
from camp_core.integrations import (
    diffusion_planner_v25_industrial_evaluation_contract_v3 as producer,
)
from camp_core.integrations import (
    diffusion_planner_v25_industrial_evaluation_review_v2 as v2_reviewer,
)
from camp_core.integrations import (
    diffusion_planner_v25_industrial_evaluation_review_v3 as reviewer,
)
from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact
from scripts.integrations.freeze_diffusion_planner_v25_industrial_evaluation_contract_v3 import (
    freeze_contract_v3,
)
from scripts.integrations.materialize_diffusion_planner_v25_industrial_evaluation_capability_matrix_v3 import (
    materialize_v3,
)
from scripts.integrations.review_diffusion_planner_v25_industrial_evaluation_capability_matrix_v3 import (
    review_matrix_v3,
)
from scripts.integrations.review_diffusion_planner_v25_industrial_evaluation_contract_v3 import (
    review_contract_v3,
)


def _contract() -> dict:
    return producer.evaluation_contract_v3()


def _leaf(contract: dict, leaf_id: str) -> dict:
    return next(
        row for row in contract["scalar_leaf_registry"] if row["leaf_id"] == leaf_id
    )


def _both_reject(contract: dict) -> None:
    with pytest.raises(ValueError):
        producer.validate_evaluation_contract_v3(contract)
    with pytest.raises(ValueError):
        reviewer.review_contract_v3_literal(contract)


def test_v3_exact_161_leaf_semantic_and_test_topology() -> None:
    contract = _contract()
    assert producer.validate_evaluation_contract_v3(contract) == contract
    assert reviewer.review_contract_v3_literal(contract) == contract
    assert contract["scalar_leaf_count"] == 161
    assert len({row["leaf_id"] for row in contract["scalar_leaf_registry"]}) == 161
    counts = {
        kind: sum(row["test_type"] == kind for row in contract["scalar_leaf_registry"])
        for kind in ("noninferiority", "descriptive", "not_testable")
    }
    assert counts == {
        "noninferiority": 110,
        "descriptive": 9,
        "not_testable": 42,
    }
    topology = contract["decision_topology"]
    assert topology["holm_order"] == "stable_ascending_(p_value,leaf_id)"
    assert topology["holm_comparison"] == "p_value<=alpha/(m-i+1)"
    assert topology["holm_stop_rule"] == "stop_at_first_non_rejection"
    assert topology["ordinary_ci_role"].startswith(
        "unadjusted 95pct intervals are descriptive only"
    )
    assert topology["current_claim_gate_authorized"] is False
    assert topology["weighted_compensation_allowed"] is False


def test_collision_onset_proxy_is_nonnegative_and_typed_missing() -> None:
    approaching = producer.collision_onset_relative_closing_speed_proxy(
        [0.0, 0.0],
        [1.0, 0.0],
        [3.0, 0.0],
        [3.0, 0.0],
        dt_s=1.0,
        continuous_sat_entry_fraction=0.5,
    )
    assert approaching == {
        "status": "computed",
        "value": 1.0,
        "reason": "nonnegative_collision_onset_kinematic_proxy",
    }
    separating = producer.collision_onset_relative_closing_speed_proxy(
        [0.0, 0.0],
        [-1.0, 0.0],
        [3.0, 0.0],
        [3.0, 0.0],
        dt_s=1.0,
        continuous_sat_entry_fraction=0.5,
    )
    assert separating["status"] == "computed"
    assert separating["value"] == 0.0
    initial = producer.collision_onset_relative_closing_speed_proxy(
        [0.0, 0.0],
        [0.0, 0.0],
        [1.0, 0.0],
        [1.0, 0.0],
        dt_s=0.1,
        continuous_sat_entry_fraction=0.0,
        initial_overlap=True,
    )
    assert initial["reason"] == "initial_overlap_has_no_false_to_true_onset_interval"
    no_prior = producer.collision_onset_relative_closing_speed_proxy(
        [0.0, 0.0],
        [0.0, 0.0],
        [1.0, 0.0],
        [1.0, 0.0],
        dt_s=0.1,
        continuous_sat_entry_fraction=0.0,
        has_preceding_interval=False,
    )
    assert no_prior["reason"] == "no_preceding_interval_for_collision_onset"
    zero_norm = producer.collision_onset_relative_closing_speed_proxy(
        [0.0, 0.0],
        [1.0, 0.0],
        [2.0, 0.0],
        [-1.0, 0.0],
        dt_s=1.0,
        continuous_sat_entry_fraction=0.5,
    )
    assert zero_norm["reason"] == "coincident_centroids_at_contact"
    no_entry = producer.collision_onset_relative_closing_speed_proxy(
        [0.0, 0.0],
        [1.0, 0.0],
        [3.0, 0.0],
        [3.0, 0.0],
        dt_s=1.0,
        continuous_sat_entry_fraction=None,
    )
    assert no_entry["reason"] == "no_finite_unique_continuous_sat_entry"
    nonfinite = producer.collision_onset_relative_closing_speed_proxy(
        [0.0, 0.0],
        [np.nan, 0.0],
        [3.0, 0.0],
        [3.0, 0.0],
        dt_s=1.0,
        continuous_sat_entry_fraction=0.5,
    )
    assert nonfinite["reason"] == "nonfinite_or_invalid_interval_input"
    onset = _leaf(_contract(), producer.COLLISION_ONSET_ID)
    assert onset["direction"] == "lower"
    assert "max(0,-dot(r_tau,v_rel_tau)" in onset["formula"]
    assert "delta-v" not in onset["formula"].lower()


def test_executable_student_t_and_holm_boundaries() -> None:
    assert producer.oriented_paired_cluster_delta(
        "lower", [1.0, 2.0], [2.0, 4.0]
    ).tolist() == [1.0, 2.0]
    assert producer.oriented_paired_cluster_delta(
        "higher", [2.0, 4.0], [1.0, 2.0]
    ).tolist() == [1.0, 2.0]
    positive = producer.one_sided_student_t_p_value([1.0, 1.0], 0.0)
    boundary = producer.one_sided_student_t_p_value([0.0, 0.0], 0.0)
    negative = producer.one_sided_student_t_p_value([-1.0, -1.0], 0.0)
    assert (positive["p_value"], boundary["p_value"], negative["p_value"]) == (
        0.0,
        1.0,
        1.0,
    )
    variable = producer.one_sided_student_t_p_value([0.5, 1.5, 2.0], 0.25)
    assert variable["p_value"] == pytest.approx(
        reviewer.local_one_sided_student_t_p_value([0.5, 1.5, 2.0], 0.25)
    )
    holm = producer.holm_step_down(
        {"b": 0.01, "a": 0.01, "c": 0.2}, ["a", "b", "c"]
    )
    assert [row["leaf_id"] for row in holm["ordered_decisions"]] == ["a", "b", "c"]
    assert [row["rejected"] for row in holm["ordered_decisions"]] == [
        True,
        True,
        False,
    ]
    assert reviewer.local_holm_step_down(
        {"b": 0.01, "a": 0.01, "c": 0.2}, ["a", "b", "c"]
    ) == [("a", True), ("b", True), ("c", False)]
    equality = producer.holm_step_down({"a": 0.025, "b": 0.04}, ["a", "b"])
    assert [row["rejected"] for row in equality["ordered_decisions"]] == [
        True,
        True,
    ]
    stopped = producer.holm_step_down({"a": 0.03, "b": 0.031}, ["a", "b"])
    assert [row["rejected"] for row in stopped["ordered_decisions"]] == [
        False,
        False,
    ]
    with pytest.raises(ValueError):
        producer.holm_step_down({"a": 0.01}, ["a", "b"])
    with pytest.raises(ValueError):
        producer.one_sided_student_t_p_value([1.0, np.nan], 0.0)


@pytest.mark.parametrize(
    ("leaf_id", "field", "replacement"),
    [
        ("safety.collision_any", "formula", "forged"),
        ("safety.max_drac_mps2", "units", "score"),
        (
            "safety.certified_red_crossing_any",
            "opportunity_denominator",
            "red ticks only",
        ),
        ("operations.completion_fraction", "test_type", "descriptive"),
        (
            "comfort.body_longitudinal_filtered_acceleration_abs_p95",
            "familywise_method",
            "none",
        ),
    ],
)
def test_independent_semantic_oracle_survives_synchronized_digest_repin(
    monkeypatch: pytest.MonkeyPatch,
    leaf_id: str,
    field: str,
    replacement: object,
) -> None:
    contract = _contract()
    _leaf(contract, leaf_id)[field] = replacement
    monkeypatch.setattr(
        reviewer,
        "EXPECTED_LEAF_REGISTRY_SHA256",
        v2.canonical_sha256(contract["scalar_leaf_registry"]),
    )
    monkeypatch.setattr(
        reviewer, "EXPECTED_CONTRACT_SHA256", v2.canonical_sha256(contract)
    )
    with pytest.raises(ValueError, match="scalar semantic drift"):
        reviewer.review_contract_v3_literal(contract)


def test_unknown_omitted_duplicate_and_family_missing_fail_closed() -> None:
    for mutation in ("unknown", "omit", "duplicate"):
        contract = _contract()
        if mutation == "unknown":
            contract["scalar_leaf_registry"][0]["leaf_id"] = "unknown"
        elif mutation == "omit":
            contract["scalar_leaf_registry"].pop()
            contract["scalar_leaf_count"] -= 1
        else:
            contract["scalar_leaf_registry"].append(
                copy.deepcopy(contract["scalar_leaf_registry"][0])
            )
            contract["scalar_leaf_count"] += 1
        _both_reject(contract)
    with pytest.raises(ValueError):
        producer.holm_step_down({}, ["a"])


def _write(path: Path, name: str, value: object) -> str:
    raw = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")
    (path / name).write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _synthetic_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    paths = {}
    synthetic = {}
    for name in v2.SEALED_SOURCES:
        path = tmp_path / name
        path.mkdir()
        if name == "evaluation_v2_contract":
            report = {
                "source_capability_audit": {
                    "actor_fields": ["position"],
                    "spawn_fields": ["goal"],
                    "all_map_assets_present_and_sha_bound": True,
                    "all_route_assets_present_and_sha_bound": True,
                    "full_polygon_capability": "available",
                    "ordered_route_capability": "available",
                },
                "contract": {
                    "endpoint_catalog": {
                        key: {}
                        for key in (
                            "collision",
                            "dynamic_proximity",
                            "road_containment",
                            "route",
                            "goal",
                            "certified_red_crossing",
                            "speed",
                            "vehicle_body_planar_kinematic_proxy",
                        )
                    },
                    "grids": {"speed_tolerance_mps": [0.0, 0.05, 0.1, 0.2]},
                    "geometry": {"dt_s": 0.1, "boxcar_kernel": [1 / 11] * 11},
                },
            }
            _write(path, "report.json", report)
        elif name == "metric_contract":
            _write(
                path,
                "report.json",
                {
                    "contract": {
                        "body_proxy": {
                            "source_fields": ["position_xy", "heading"],
                            "filter": "11-point boxcar",
                        }
                    }
                },
            )
        elif name == "execution":
            report_sha = _write(path, "report.json", {"opaque": "not read"})
            _write(path, "artifact_report.json", {"execution_report_sha256": report_sha})
        else:
            _write(path, "report.json", {"structural": name})
        root = seal_artifact(path)
        manifest = {}
        for line in (path / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
            sha, filename = line.split("  ", 1)
            manifest[filename] = sha
        synthetic[name] = {
            "root": root,
            "review_root": None,
            "required_inventory": manifest,
        }
        paths[name] = path
    review_for = {
        "execution": "execution_review",
        "evaluation_v2_contract": "evaluation_v2_contract_review",
        "evaluation_v2_materialization": "evaluation_v2_materialization_review",
        "metric_contract": "metric_contract_review",
    }
    for name, row in synthetic.items():
        row["review_root"] = (
            synthetic[review_for[name]]["root"] if name in review_for else None
        )
    monkeypatch.setattr(v2, "SEALED_SOURCES", synthetic)
    monkeypatch.setattr(
        v2_reviewer,
        "SOURCE_ROOTS",
        {
            name: (row["root"], row["required_inventory"])
            for name, row in synthetic.items()
        },
    )
    monkeypatch.setattr(
        v2_reviewer,
        "SOURCE_REVIEW_ROOTS",
        {name: row["review_root"] for name, row in synthetic.items()},
    )
    return paths


def test_v3_capability_reseals_same_inventory_without_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = _contract()
    sources = _synthetic_sources(tmp_path, monkeypatch)
    matrix = producer.capability_matrix_v3(contract, sources)
    assert producer.validate_capability_matrix_v3(matrix, contract, sources) == matrix
    assert reviewer.review_capability_v3_literal(matrix, contract, sources) == matrix
    assert matrix["scalar_leaf_count"] == 161
    assert matrix["outcome_values_read"] is False
    forged = copy.deepcopy(matrix)
    forged["rows"][0]["evidence_class"] = "directly_reconstructable"
    with pytest.raises(ValueError):
        producer.validate_capability_matrix_v3(forged, contract, sources)
    with pytest.raises(ValueError):
        reviewer.review_capability_v3_literal(forged, contract, sources)


def test_v3_full_atomic_seal_chain_is_zero_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = _contract()
    sources = _synthetic_sources(tmp_path / "sources", monkeypatch)
    contract_dir = tmp_path / "contract"
    contract_root = freeze_contract_v3(contract_dir)
    assert json.loads((contract_dir / "report.json").read_text())["contract"] == contract
    contract_review_dir = tmp_path / "contract_review"
    contract_review_root = review_contract_v3(
        contract_review_dir, contract_dir, contract_root
    )
    matrix_dir = tmp_path / "matrix"
    matrix_root = materialize_v3(
        matrix_dir,
        contract_dir,
        contract_root,
        contract_review_dir,
        contract_review_root,
        sources,
    )
    matrix_review_dir = tmp_path / "matrix_review"
    matrix_review_root = review_matrix_v3(
        matrix_review_dir,
        contract_dir,
        contract_root,
        contract_review_dir,
        contract_review_root,
        matrix_dir,
        matrix_root,
        sources,
    )
    for directory, root in (
        (contract_dir, contract_root),
        (contract_review_dir, contract_review_root),
        (matrix_dir, matrix_root),
        (matrix_review_dir, matrix_review_root),
    ):
        assert len(root) == 64
        report = json.loads((directory / "report.json").read_text())
        assert report["model_pool_selector_call_count"] == 0
        assert report["outcome_values_read"] is False


def test_v3_reviewer_does_not_import_v3_producer_or_decision_oracle() -> None:
    source = inspect.getsource(reviewer)
    assert "industrial_evaluation_contract_v3" not in source
    assert "from camp_core.integrations import diffusion_planner_v25_industrial_evaluation_contract_v3" not in source
