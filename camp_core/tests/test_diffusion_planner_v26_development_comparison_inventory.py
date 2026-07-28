from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "camp_core") not in sys.path:
    sys.path.insert(0, str(ROOT / "camp_core"))

from camp_core.integrations import (  # noqa: E402
    diffusion_planner_v26_development_comparison_inventory as inventory,
)
from camp_core.integrations.diffusion_planner_v26_source_authority import (  # noqa: E402
    build_v26_source_signal_config,
    v26_source_inventory_binding,
)


def _sha(index: int) -> str:
    return f"{index:064x}"


def _candidate(index: int, *, physical: str | None = None) -> dict[str, object]:
    route_id = f"v26-source-authoritative/family-{index % 2}/{_sha(1000 + index)}"
    return {
        "schema_version": inventory.SOURCE_CANDIDATE_SCHEMA_VERSION,
        "family_id": f"family-{index % 2}",
        "route_id": route_id,
        "route_identity_sha256": _sha(2000 + index),
        "provisional_corridor_id": _sha(3000 + index),
        "physical_route_identity_sha256": physical or _sha(4000 + index),
        "source_map_sha256": _sha(5000 + index % 2),
        "derived_geometry_sha256": _sha(6000 + index),
        "source_artifact_sha256": _sha(7000 + index % 2),
        "source_projection_sha256": _sha(8000 + index % 2),
        "source_inventory_sha256": _sha(9000 + index % 2),
        "source_event_identity_sha256": _sha(10000 + index % 3),
        "event_manifest_sha256": _sha(11000 + index % 3),
        "risk_stratum_sha256": _sha(12000 + index % 4),
        "geometry_stratum": "short_le_100m" if index % 2 else "medium_100_to_200m",
        "source_stratum": {
            "traffic_light": index % 2 == 0,
            "branch_intersection": index % 3 == 0,
            "tight_corridor": True,
            "short_progress_opportunity": index % 2 == 1,
        },
        "route_lanelet_ids": [100000 + index],
        "boundary_ids": [200000 + index],
        "minimum_source_corridor_width_m": 4.0,
        "source_arc_length_m": 80.0,
        "route_length_m": 90.0,
        "route_spec": {
            "map_path": f"/maps/{index % 2}.osm",
            "lanelet_ids": [100000 + index],
            "start_pose": [float(index) * 100.0, 0.0, 0.0],
            "goal_pose": [float(index) * 100.0 + 90.0, 0.0, 0.0],
            "route_length_m": 90.0,
        },
        "identity_only_route_sha256": _sha(13000 + index),
        "signal_authority_mode": "certified_no_signal",
        "signal_adapter_id": "camp_dp_v26_certified_no_signal_absence_adapter_v1",
        "eligibility": {
            "schema_version": inventory.ELIGIBILITY_SCHEMA_VERSION,
            "status": "passed_v26_native_source_preflight",
            "failure_class": None,
            "failure_reason": None,
            "exact_route_connectivity": True,
            "source_signal_adapter_bound": True,
            "model_dp_gpu_latent_candidate_calls": inventory._zero_calls(),
        },
        "_centerline_samples_m": [[float(index) * 100.0, 0.0], [float(index) * 100.0 + 90.0, 0.0]],
        "_centerline_headings_rad": [0.0, 0.0],
    }


def _source_collection(candidates: list[dict[str, object]]) -> dict[str, object]:
    return {
        "zero_model_calls": inventory._zero_calls(),
        "training_identities": [
            {
                "route_id": "training/route",
                "corridor_id": "training/corridor",
                "source_map_sha256": _sha(5000),
                "derived_geometry_sha256": _sha(600),
                "source_event_identity_sha256": _sha(601),
                "physical_route_identity_sha256": _sha(602),
            }
        ],
        "candidates": candidates,
        "families": [
            {
                "family_id": "family-0",
                "source_status": "available_v26_native_source_bound",
                "candidate_universe_count": len(candidates) // 2,
                "eligible_preflight_count": len(candidates) // 2,
                "typed_failure_count": 0,
            },
            {
                "family_id": "family-1",
                "source_status": "typed_source_map_unavailable_no_v26_native_path",
                "candidate_universe_count": 0,
                "eligible_preflight_count": 0,
                "typed_failure_count": 0,
            },
        ],
    }


def _build(candidates: list[dict[str, object]]) -> dict[str, object]:
    return inventory.build_development_comparison_inventory(
        source_collection=_source_collection(candidates),
        camp_head="a" * 40,
        fixed_dp_checkpoint={"path": "/fixed/diffusion_planner.pth", "sha256": _sha(700)},
        adapted_selector={"artifact_role": "camp_dp_v26_adapted_selector_weights_v1", "assets": {}},
        reference_selector={"artifact_role": "v25_zero_shot_reference_read_only", "reference": {}},
        final_training_population_sha256=_sha(701),
        revision_plan_sha256=_sha(702),
    )


def test_identity_only_selection_freezes_one_hundred_independent_route_corridors() -> None:
    manifest = _build([_candidate(index) for index in range(130)])
    assert inventory.validate_development_comparison_inventory(manifest) == manifest
    assert manifest["planned_denominator"] == {
        "cluster_is_independent_n": True,
        "planned": 100,
        "complete": 0,
        "typed_failure": 0,
        "unattempted": 100,
    }
    assert len(manifest["selected_clusters"]) == 100
    assert len({row["corridor_id"] for row in manifest["selected_clusters"]}) == 100
    assert manifest["selection"]["capacity_ceiling"] is False
    assert manifest["invocation_counts"] == inventory._zero_calls()
    assert manifest["payload_read"] is False
    assert manifest["endpoint_contract"]["weighted_total_score"] is False
    assert "SafetyCost" not in json.dumps(manifest)


def test_physical_training_collision_is_excluded_not_relabelled_by_route_or_seed() -> None:
    colliding = _candidate(0, physical=_sha(602))
    manifest = _build([colliding, *[_candidate(index) for index in range(1, 101)]])
    assert manifest["disjointness"]["physical_geometry_collision_count"] == 1
    assert manifest["candidate_universe"]["route_disjoint_eligible_count"] == 100
    assert all(
        row["physical_route_identity_sha256"] != _sha(602)
        for row in manifest["selected_clusters"]
    )
    assert manifest["disjointness"]["different_seed_or_state_creates_new_route"] is False


def test_no_disjoint_source_candidate_fails_closed_and_validator_rejects_payload_read() -> None:
    with pytest.raises(ValueError, match="no source-authoritative route-disjoint candidate"):
        _build([_candidate(0, physical=_sha(602))])
    manifest = _build([_candidate(index) for index in range(3)])
    bad = copy.deepcopy(manifest)
    bad["payload_read"] = True
    bad["inventory_sha256"] = inventory.canonical_json_sha256(
        {key: value for key, value in bad.items() if key != "inventory_sha256"}
    )
    with pytest.raises(ValueError, match="identity-only contract"):
        inventory.validate_development_comparison_inventory(bad)


def test_composite_tuple_is_uniform_and_rebuild_keeps_ordered_selection_bytes_stable() -> None:
    manifest = _build([_candidate(index) for index in range(103)])
    assert manifest["disjointness"]["composite_fields"] == list(
        inventory.COMPOSITE_IDENTITY_FIELDS
    )
    selected = manifest["selected_clusters"]
    assert inventory.comparison_composite_identity(selected[0]) == (
        selected[0]["route_id"],
        selected[0]["corridor_id"],
        selected[0]["physical_route_identity_sha256"],
        selected[0]["source_event_identity_sha256"],
    )
    rebuilt = _build([_candidate(index) for index in range(103)])
    inventory.require_selection_rebuild_stability(previous=manifest, rebuilt=rebuilt)
    changed = copy.deepcopy(rebuilt)
    changed["selected_clusters"][0], changed["selected_clusters"][1] = (
        changed["selected_clusters"][1],
        changed["selected_clusters"][0],
    )
    with pytest.raises(ValueError, match="selected identity bytes drifted"):
        inventory.require_selection_rebuild_stability(previous=manifest, rebuilt=changed)


def test_input_sha_bindings_are_required_and_malformed_values_fail_closed() -> None:
    manifest = _build([_candidate(index) for index in range(3)])
    assert manifest["input_bindings"] == {
        "final_training_population_sha256": _sha(701),
        "revision_plan_sha256": _sha(702),
    }
    drifted = copy.deepcopy(manifest)
    drifted["input_bindings"]["revision_plan_sha256"] = "not-a-sha"
    drifted["inventory_sha256"] = inventory.canonical_json_sha256(
        {key: value for key, value in drifted.items() if key != "inventory_sha256"}
    )
    with pytest.raises(ValueError, match="revision_plan_sha256"):
        inventory.validate_development_comparison_inventory(drifted)


def test_source_inventory_binding_reuses_exact_authoritative_map_without_signal_fallback(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.osm"
    source.write_text(
        """<osm version=\"0.6\">
<node id=\"1\" lat=\"0.665608\" lon=\"-0.559376\"/>
<node id=\"2\" lat=\"0.665609\" lon=\"-0.559375\"/>
<node id=\"3\" lat=\"0.665610\" lon=\"-0.559374\"/>
<way id=\"10\"><nd ref=\"1\"/><nd ref=\"2\"/></way>
<way id=\"11\"><nd ref=\"1\"/><nd ref=\"2\"/></way>
<way id=\"12\"><nd ref=\"2\"/><nd ref=\"3\"/></way>
<relation id=\"1\"><member type=\"relation\" ref=\"100\" role=\"regulatory_element\"/><tag k=\"type\" v=\"lanelet\"/></relation>
<relation id=\"100\"><member type=\"way\" ref=\"10\" role=\"refers\"/><member type=\"way\" ref=\"11\" role=\"ref_line\"/><member type=\"way\" ref=\"12\" role=\"light_bulbs\"/><tag k=\"type\" v=\"regulatory_element\"/><tag k=\"subtype\" v=\"traffic_light\"/></relation>
</osm>""",
        encoding="utf-8",
    )
    map_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    binding = v26_source_inventory_binding(source, map_sha)
    schedule = {
        "source_artifact_sha256": _sha(1),
        "event_manifest_sha256": _sha(2),
        "route_record": {
            "identity_sha256": _sha(3),
            "source_map_path": str(source),
            "source_map_sha256": map_sha,
            "source_geometry_sha256": _sha(4),
            "lanelet_ids": [1],
            "source_stratum": {
                "traffic_light": True,
                "branch_intersection": False,
                "tight_corridor": True,
                "short_progress_opportunity": False,
            },
        },
    }
    direct = build_v26_source_signal_config(
        schedule=schedule, family={"sidecar": None}, route_sha256=_sha(5)
    )
    reused = build_v26_source_signal_config(
        schedule=schedule,
        family={"sidecar": None},
        route_sha256=_sha(5),
        source_inventory_binding=binding,
    )
    assert reused == direct
    source_text = Path(inventory.__file__).read_text(encoding="utf-8")
    assert "validate_diffusion_planner_v25_fair_nonholdout" not in source_text
    assert "census_diffusion_planner_v24_routes" not in source_text
