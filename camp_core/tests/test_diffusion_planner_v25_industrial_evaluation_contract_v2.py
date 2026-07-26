from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path

import pytest

from camp_core.integrations import (
    diffusion_planner_v25_industrial_evaluation_contract_v2 as producer,
)
from camp_core.integrations import (
    diffusion_planner_v25_industrial_evaluation_review_v2 as reviewer,
)
from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact
from scripts.integrations.freeze_diffusion_planner_v25_industrial_evaluation_contract_v2 import (
    freeze_contract_v2,
)
from scripts.integrations.materialize_diffusion_planner_v25_industrial_evaluation_capability_matrix_v2 import (
    materialize_v2,
)
from scripts.integrations.review_diffusion_planner_v25_industrial_evaluation_capability_matrix_v2 import (
    review_matrix_v2,
)
from scripts.integrations.review_diffusion_planner_v25_industrial_evaluation_contract_v2 import (
    review_contract_v2,
)


def _contract() -> dict:
    return producer.evaluation_contract_v2()


def _both_reject(contract: dict) -> None:
    with pytest.raises(ValueError):
        producer.validate_evaluation_contract_v2(contract)
    with pytest.raises(ValueError):
        reviewer.review_contract_v2_literal(contract)


def _leaf(contract: dict, leaf_id: str) -> dict:
    return next(row for row in contract["scalar_leaf_registry"] if row["leaf_id"] == leaf_id)


def test_v2_contract_has_exact_56_parent_161_scalar_topology() -> None:
    contract = _contract()
    assert producer.validate_evaluation_contract_v2(contract) == contract
    assert reviewer.review_contract_v2_literal(contract) == contract
    assert contract["parent_endpoint_count"] == 56
    assert contract["scalar_leaf_count"] == 161
    ids = [row["leaf_id"] for row in contract["scalar_leaf_registry"]]
    assert len(ids) == len(set(ids)) == 161
    assert set(ids) == set(reviewer._expected_leaf_ids())
    assert contract["claim_authorized"] is False
    assert contract["outcome_values_read"] is False
    assert contract["model_pool_selector_call_count"] == 0


def test_all_hidden_threshold_stat_and_budget_leaves_are_individual() -> None:
    contract = _contract()
    ids = {row["leaf_id"] for row in contract["scalar_leaf_registry"]}
    assert "safety.clearance_m_le_0p5m_duration_s" in ids
    assert "safety.drac_mps2_ge_5mps2_episode_count" in ids
    assert "operations.speed_excess_gt_0p1mps_duration_s" in ids
    assert "comfort.body_longitudinal_filtered_acceleration_abs_p99" in ids
    assert "comfort.filtered_lateral_jerk_abs_gt_5mps3_duration_s" in ids
    assert "realtime.pool_generation_latency_median_ms" in ids
    assert "realtime.end_to_end_max_overrun_100ms_ms" in ids
    assert not any(row["leaf_id"] == "safety.critical_exposure_duration_s" for row in contract["scalar_leaf_registry"])


@pytest.mark.parametrize(
    ("leaf_id", "field", "replacement"),
    [
        ("safety.clearance_m_le_0p5m_duration_s", "units", "score"),
        ("safety.drac_mps2_ge_5mps2_episode_count", "direction", "higher"),
        ("operations.speed_excess_gt_0p1mps_duration_s", "formula", "omitted tolerance"),
        ("comfort.body_longitudinal_filtered_acceleration_abs_p99", "units", "m/s"),
        ("realtime.pool_generation_latency_median_ms", "guardrail_role", "descriptive_only"),
        ("realtime.end_to_end_max_overrun_100ms_ms", "multiplicity_family", "other"),
    ],
)
def test_leaf_semantic_mutations_fail_closed(
    leaf_id: str, field: str, replacement: object
) -> None:
    contract = _contract()
    _leaf(contract, leaf_id)[field] = replacement
    _both_reject(contract)


def test_added_deleted_duplicate_or_renamed_leaf_fails_closed() -> None:
    for mutation in ("delete", "duplicate", "rename"):
        contract = _contract()
        if mutation == "delete":
            contract["scalar_leaf_registry"].pop()
            contract["scalar_leaf_count"] -= 1
        elif mutation == "duplicate":
            contract["scalar_leaf_registry"].append(
                copy.deepcopy(contract["scalar_leaf_registry"][0])
            )
            contract["scalar_leaf_count"] += 1
        else:
            contract["scalar_leaf_registry"][0]["leaf_id"] = "safety.unknown"
        _both_reject(contract)


def test_collision_onset_proxy_is_reconstructable_but_delta_v_severity_missing() -> None:
    contract = _contract()
    onset = _leaf(
        contract,
        "safety.collision_onset_relative_closing_speed_kinematic_proxy_mps",
    )
    assert onset["evidence_class"] == "reconstructable_with_frozen_transform"
    assert onset["source_binding_id"] == "execution_kinematics_geometry"
    assert "last noncollision interval" in onset["formula"]
    assert "first contact fraction" in onset["formula"]
    for leaf_id in (
        "safety.collision_delta_v_mps",
        "safety.collision_contact_severity",
    ):
        row = _leaf(contract, leaf_id)
        assert row["evidence_class"] == "evidence_missing"
        assert row["guardrail_role"] == "evidence_missing_not_testable"


def test_statistics_topology_is_fixed_no_weighted_compensation() -> None:
    contract = _contract()
    topology = contract["decision_topology"]
    assert topology["familywise_method"] == producer.FAMILYWISE_METHOD
    assert topology["familywise_alpha"] == 0.05
    assert topology["weighted_compensation_allowed"] is False
    assert topology["current_claim_gate_authorized"] is False
    assert "intersection_union" in topology["hard_safety_combination"]
    assert "intersection_union" in topology["guardrail_combination"]
    assert {
        leaf for members in topology["families"].values() for leaf in members
    } == {row["leaf_id"] for row in contract["scalar_leaf_registry"]}


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("decision_topology", "familywise_method"), "future choose later"),
        (("decision_topology", "familywise_alpha"), 0.1),
        (("decision_topology", "weighted_compensation_allowed"), True),
        (("decision_topology", "current_claim_gate_authorized"), True),
        (("scalar_leaf_registry", 0, "claim_gate_state"), "pass"),
        (("scalar_leaf_registry", 0, "btw_applicability"), "not_applicable"),
    ],
)
def test_statistical_decision_mutations_fail_closed(path: tuple, value: object) -> None:
    contract = _contract()
    current = contract
    for token in path[:-1]:
        current = current[token]
    current[path[-1]] = value
    _both_reject(contract)


def _write(path: Path, name: str, value: object) -> str:
    raw = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")
    (path / name).write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _nested_contract_report() -> dict:
    return {
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
                "collision": {},
                "dynamic_proximity": {},
                "road_containment": {},
                "route": {},
                "goal": {},
                "certified_red_crossing": {},
                "speed": {},
                "vehicle_body_planar_kinematic_proxy": {},
            },
            "grids": {"speed_tolerance_mps": [0.0, 0.05, 0.1, 0.2]},
            "geometry": {"dt_s": 0.1, "boxcar_kernel": [1 / 11] * 11},
        },
    }


def _synthetic_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    synthetic = {}
    for name in producer.SEALED_SOURCES:
        path = tmp_path / name
        path.mkdir()
        if name == "evaluation_v2_contract":
            _write(path, "report.json", _nested_contract_report())
            _write(path, "HEADS", {"head": name})
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
            _write(path, "HEADS", {"head": name})
        elif name == "execution":
            report_sha = _write(path, "report.json", {"opaque": "not read"})
            _write(path, "artifact_report.json", {"execution_report_sha256": report_sha})
            _write(path, "HEADS", {"head": name})
        else:
            _write(path, "report.json", {"structural": name})
            if name != "metric_contract_review":
                _write(path, "HEADS", {"head": name})
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
    for name in synthetic:
        review_name = (
            "execution_review"
            if name == "execution"
            else "evaluation_v2_contract_review"
            if name == "evaluation_v2_contract"
            else "evaluation_v2_materialization_review"
            if name == "evaluation_v2_materialization"
            else "metric_contract_review"
            if name == "metric_contract"
            else None
        )
        synthetic[name]["review_root"] = (
            synthetic[review_name]["root"] if review_name else None
        )
    monkeypatch.setattr(producer, "SEALED_SOURCES", synthetic)
    monkeypatch.setattr(
        reviewer,
        "SOURCE_ROOTS",
        {
            name: (row["root"], row["required_inventory"])
            for name, row in synthetic.items()
        },
    )
    monkeypatch.setattr(
        reviewer,
        "SOURCE_REVIEW_ROOTS",
        {name: row["review_root"] for name, row in synthetic.items()},
    )
    return paths


def test_capability_matrix_rebuilds_exact_sealed_inventory_and_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = _synthetic_sources(tmp_path, monkeypatch)
    contract = _contract()
    matrix = producer.capability_matrix_v2(contract, sources)
    assert producer.validate_capability_matrix_v2(matrix, contract, sources) == matrix
    assert reviewer.review_capability_v2_literal(matrix, contract, sources) == matrix
    assert matrix["scalar_leaf_count"] == 161
    assert matrix["outcome_values_read"] is False
    onset = next(
        row
        for row in matrix["rows"]
        if row["leaf_id"]
        == "safety.collision_onset_relative_closing_speed_kinematic_proxy_mps"
    )
    assert onset["evidence_class"] == "reconstructable_with_frozen_transform"
    assert onset["canonical_json_pointers"]
    assert all("*" not in item["inventory_file"] for item in onset["evidence_inventory"])

    forged = copy.deepcopy(matrix)
    forged["rows"][0]["evidence_inventory"][0]["inventory_file_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        producer.validate_capability_matrix_v2(forged, contract, sources)
    with pytest.raises(ValueError):
        reviewer.review_capability_v2_literal(forged, contract, sources)


def test_capability_missing_field_pointer_and_classification_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = _synthetic_sources(tmp_path, monkeypatch)
    contract = _contract()
    matrix = producer.capability_matrix_v2(contract, sources)
    forged = copy.deepcopy(matrix)
    target = next(row for row in forged["rows"] if row["canonical_json_pointers"])
    target["canonical_json_pointers"] = target["canonical_json_pointers"][1:]
    with pytest.raises(ValueError):
        producer.validate_capability_matrix_v2(forged, contract, sources)
    with pytest.raises(ValueError):
        reviewer.review_capability_v2_literal(forged, contract, sources)

    forged = copy.deepcopy(matrix)
    forged["rows"][0]["evidence_class"] = "directly_reconstructable"
    with pytest.raises(ValueError):
        producer.validate_capability_matrix_v2(forged, contract, sources)
    with pytest.raises(ValueError):
        reviewer.review_capability_v2_literal(forged, contract, sources)


def test_v2_full_atomic_seal_chain_is_zero_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sources = _synthetic_sources(tmp_path / "sources", monkeypatch)
    contract_dir = tmp_path / "contract"
    contract_root = freeze_contract_v2(contract_dir)
    contract_review_dir = tmp_path / "contract_review"
    contract_review_root = review_contract_v2(
        contract_review_dir, contract_dir, contract_root
    )
    matrix_dir = tmp_path / "matrix"
    matrix_root = materialize_v2(
        matrix_dir,
        contract_dir,
        contract_root,
        contract_review_dir,
        contract_review_root,
        sources,
    )
    matrix_review_dir = tmp_path / "matrix_review"
    matrix_review_root = review_matrix_v2(
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
        report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
        assert report["model_pool_selector_call_count"] == 0
        assert report["outcome_values_read"] is False


def test_reviewer_is_separate_role_literal_oracle() -> None:
    source = inspect.getsource(reviewer)
    assert "import diffusion_planner_v25_industrial_evaluation_contract_v2" not in source
    assert "from camp_core.integrations import (" not in source
    assert "from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_contract_v2" not in source
