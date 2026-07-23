from __future__ import annotations

import copy
import hashlib

import pytest

from camp_core.integrations.diffusion_planner_v25_split import (
    validate_signal_complete_map_license,
    validate_v25_holdout_zero_overlap,
    validate_v25_replacement_holdout_zero_overlap,
    validate_v25_zero_overlap,
)


def _sha(character: str) -> str:
    return hashlib.sha256(character.encode("ascii")).hexdigest()


def _rows() -> list[dict]:
    rows = []
    for index, split in enumerate(("train", "calibration", "fresh_b2")):
        character = chr(ord("a") + index)
        rows.append(
            {
                "split": split,
                "source_family": "project_synthetic_signal_complete",
                "map_geometry_sha256": _sha(character),
                "intersection_sha256": _sha(chr(ord("d") + index)),
                "corridor_sha256": _sha(chr(ord("g") + index)),
                "route_family_sha256": _sha(chr(ord("j") + index)),
                "semantic_parameter_block_sha256": _sha(chr(ord("m") + index)),
                "seed_namespace": f"v25-{split}",
                "route_identity_sha256": _sha(chr(ord("p") + index)),
                "scenario_family": "red_light_phase_timing",
            }
        )
    return rows


def _rows_for_roles(roles: tuple[str, ...]) -> list[dict]:
    rows = []
    for index, split in enumerate(roles):
        token = f"{index}:{split}"
        rows.append(
            {
                "split": split,
                "source_family": f"source-{split}",
                "map_geometry_sha256": _sha(f"map:{token}"),
                "intersection_sha256": _sha(f"intersection:{token}"),
                "corridor_sha256": _sha(f"corridor:{token}"),
                "route_family_sha256": _sha(f"route-family:{token}"),
                "semantic_parameter_block_sha256": _sha(f"semantic:{token}"),
                "seed_namespace": f"v25-{split}",
                "route_identity_sha256": _sha(f"route:{token}"),
                "scenario_family": "red_light_phase_timing",
            }
        )
    return rows


def test_zero_overlap_allows_shared_source_stratum_but_not_shared_units() -> None:
    receipt = validate_v25_zero_overlap(_rows())
    assert receipt["status"] == "passed"
    assert receipt["split_row_counts"] == {
        "train": 1,
        "calibration": 1,
        "fresh_b2": 1,
    }
    assert all(
        values == ["project_synthetic_signal_complete"]
        for values in receipt["source_family_strata"].values()
    )


def test_zero_overlap_requires_every_role_and_returns_a_receipt() -> None:
    with pytest.raises(ValueError, match="must all be nonempty"):
        validate_v25_zero_overlap(_rows()[:-1])
    receipt = validate_v25_zero_overlap(_rows())
    assert receipt["schema_version"] == "camp_dp_v25_zero_overlap_receipt_v1"
    assert receipt["row_count"] == 3


def test_b3_holdout_zero_overlap_has_an_independent_complete_body() -> None:
    rows = _rows_for_roles(("train", "calibration", "fresh_b2", "fresh_b3"))
    receipt = validate_v25_holdout_zero_overlap(rows)
    assert receipt["status"] == "passed_train_calibration_b2_b3_zero_overlap"
    assert receipt["split_row_counts"]["fresh_b3"] == 1
    rows[-1]["corridor_sha256"] = rows[1]["corridor_sha256"]
    rows[-1]["map_geometry_sha256"] = rows[1]["map_geometry_sha256"]
    with pytest.raises(ValueError, match="B3 split zero-overlap"):
        validate_v25_holdout_zero_overlap(rows)


def test_b4_replacement_zero_overlap_has_an_independent_complete_body() -> None:
    roles = ("train", "calibration", "fresh_b2", "fresh_b3", "fresh_b4")
    rows = _rows_for_roles(roles)
    receipt = validate_v25_replacement_holdout_zero_overlap(rows)
    assert receipt["status"] == "passed_train_calibration_b2_b3_b4_zero_overlap"
    assert receipt["split_row_counts"] == {role: 1 for role in roles}
    rows[-1]["semantic_parameter_block_sha256"] = rows[2][
        "semantic_parameter_block_sha256"
    ]
    with pytest.raises(ValueError, match="B4 split zero-overlap"):
        validate_v25_replacement_holdout_zero_overlap(rows)


@pytest.mark.parametrize(
    "field",
    ["map_geometry_sha256", "semantic_parameter_block_sha256"],
)
def test_zero_overlap_rejects_cross_source_export_clones(field: str) -> None:
    rows = _rows()
    rows[1]["source_family"] = "external_export_clone"
    rows[1][field] = rows[0][field]
    with pytest.raises(ValueError, match="zero-overlap"):
        validate_v25_zero_overlap(rows)


@pytest.mark.parametrize(
    "field",
    [
        "map_geometry_sha256",
        "intersection_sha256",
        "corridor_sha256",
        "route_family_sha256",
        "semantic_parameter_block_sha256",
        "seed_namespace",
        "route_identity_sha256",
    ],
)
def test_zero_overlap_rejects_every_frozen_hierarchy_leak(field: str) -> None:
    rows = _rows()
    rows[1][field] = rows[0][field]
    if field in {
        "intersection_sha256",
        "corridor_sha256",
        "route_family_sha256",
    }:
        rows[1]["map_geometry_sha256"] = rows[0]["map_geometry_sha256"]
    with pytest.raises(ValueError, match="zero-overlap"):
        validate_v25_zero_overlap(rows)


def test_project_authored_signal_map_requires_repo_mit_license() -> None:
    row = {
        "map_path": "maps/fresh_b2/signal_grid_a.osm",
        "map_file_sha256": _sha("a"),
        "map_geometry_sha256": _sha("b"),
        "source_kind": "project_authored_synthetic",
        "source_reference": "repo:maps/fresh_b2/signal_grid_a.osm",
        "license_spdx": "MIT",
        "license_evidence_sha256": _sha("c"),
        "project_authored": True,
    }
    receipt = validate_signal_complete_map_license([row])
    assert receipt["all_licenses_affirmative"] is True
    invalid = copy.deepcopy(row)
    invalid["license_spdx"] = "NOASSERTION"
    with pytest.raises(ValueError, match="MIT"):
        validate_signal_complete_map_license([invalid])
