from __future__ import annotations

import copy
import importlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _sha(index: int) -> str:
    return f"{index:064x}"


def _source_stratum(index: int) -> dict[str, bool]:
    return {
        "traffic_light": index % 2 == 0,
        "branch_intersection": index % 3 == 0,
        "tight_corridor": True,
        "short_progress_opportunity": index % 5 == 0,
    }


def _fixture(revision):
    exclusion_ordinals = (1185, 1187, 1454)
    shared_corridor = _sha(20_000 + (1185 % 155))
    families = (
        "family_a",
        "family_b",
        "nishishinjuku_plus_four_track_highway",
        "family_d",
        "family_e",
        "family_f",
    )
    specs = {}
    routes = []
    for ordinal in range(1786):
        family_id = families[ordinal % len(families)]
        lanelets = [ordinal + 1]
        route_id = f"{family_id}/route-{ordinal}"
        identity = _sha(10_000 + ordinal)
        corridor = _sha(20_000 + (ordinal % 155))
        if ordinal in exclusion_ordinals:
            family_id = "nishishinjuku_plus_four_track_highway"
            lanelets = {1185: [3002114, 3002116, 423], 1187: [3002116, 423, 49], 1454: [423, 49, 54]}[ordinal]
            route_id = f"nishishinjuku_plus_four_track_highway/excluded-{ordinal}"
            identity = _sha(30_000 + ordinal)
            corridor = shared_corridor
            specs[ordinal] = {
                "route_id": route_id,
                "route_identity_sha256": identity,
                "corridor_id": corridor,
                "route_lanelet_ids": lanelets,
            }
        record = {
            "identity_sha256": identity,
            "source_map_sha256": _sha(50_000 + (ordinal % 6)),
            "lanelet_ids": lanelets,
            "source_stratum": _source_stratum(ordinal),
        }
        routes.append(
            {
                "family_id": family_id,
                "route_id": route_id,
                "corridor_id": corridor,
                "route_record": record,
                "source_artifact_sha256": _sha(60_000 + (ordinal % 6)),
                "event_manifest_sha256": _sha(70_000 + (ordinal % 6)),
            }
        )
    parent = {
        "route_plan_sha256": _sha(1),
        "denominator": copy.deepcopy(revision.ORIGINAL_DENOMINATOR),
        "routes": routes,
        "family_projections": [{"family_id": family} for family in families],
    }
    units = {}
    unit_sha = {}
    for ordinal, schedule in enumerate(routes):
        route = schedule["route_record"]
        failed = ordinal in exclusion_ordinals
        unit = {
            "unit_index": ordinal,
            "route": {
                "route_id": schedule["route_id"],
                "corridor_id": schedule["corridor_id"],
                "route_identity_sha256": route["identity_sha256"],
                "source_map_sha256": route["source_map_sha256"],
                "route_lanelet_ids": route["lanelet_ids"],
            },
            "forward_calls": copy.deepcopy(revision.ZERO_MODEL_CALLS),
            "terminal": {
                "status": "failed" if failed else "qualified",
                "failure_class": "ValueError" if failed else None,
                "failure_reason": revision.UPSTREAM_FAILURE_REASON if failed else None,
            },
        }
        if not failed:
            unit.update(
                {
                    "source_projection": {},
                    "parsed_geometry": {},
                    "signal": {},
                    "scene14d_reference": {},
                    "generator_topology": {},
                }
            )
        units[ordinal] = unit
        unit_sha[str(ordinal)] = _sha(80_000 + ordinal)
    qualification = {
        "root": "/immutable/root",
        "receipt_path": "/immutable/root/raw_receipt.json",
        "receipt_sha256": _sha(90_001),
        "manifest_path": "/immutable/root/manifest.json",
        "manifest_sha256": _sha(90_002),
        "camp_head": "a" * 40,
        "units": units,
        "unit_sha256": unit_sha,
    }
    source_quality = {
        "sidecar_manifest_path": "/immutable/nishi.json",
        "sidecar_manifest_sha256": _sha(90_003),
        "lanelet_id": 423,
        "regulatory_element_id": 1391,
        "runtime_type": "AutowareTrafficLight",
        "roles": ["light_bulbs", "refers"],
        "source_quality_finding": revision.UPSTREAM_SOURCE_QUALITY_FINDING,
    }
    return parent, qualification, source_quality, specs


def test_revision_is_exact_1783_qualified_subset_with_parent_order(monkeypatch) -> None:
    revision = importlib.import_module(
        "camp_core.integrations.diffusion_planner_v26_diversified_plan_revision"
    )
    parent, qualification, source_quality, specs = _fixture(revision)
    monkeypatch.setattr(revision, "ORIGINAL_PLAN_SHA256", parent["route_plan_sha256"])
    monkeypatch.setattr(revision, "EXCLUSION_SPECS", specs)
    monkeypatch.setattr(revision, "validate_diversified_route_plan", lambda value: copy.deepcopy(value))

    plan, review = revision.build_revised_plan(
        parent_plan=parent,
        parent_plan_file_sha256=_sha(99_001),
        qualification=qualification,
        source_quality=source_quality,
    )

    assert plan["denominator"] == revision.REVISED_DENOMINATOR
    assert len(plan["routes"]) == 1783
    assert [row["parent_ordinal"] for row in plan["routes"]] == [
        index for index in range(1786) if index not in specs
    ]
    assert review["assertions"]["all_included_parent_ordinals_qualified"] is True
    assert set(review["included"]["unit_file_sha256_by_parent_ordinal"]) == {
        str(index) for index in range(1786) if index not in specs
    }

    tampered = copy.deepcopy(plan)
    tampered["routes"][10], tampered["routes"][11] = tampered["routes"][11], tampered["routes"][10]
    try:
        revision.validate_revised_plan(tampered, parent_plan=parent)
    except ValueError as exc:
        assert "reordered or substituted" in str(exc)
    else:  # pragma: no cover - contract failure
        raise AssertionError("reordered revised plan was accepted")


def test_revision_cli_parser_requires_immutable_parent_and_receipt() -> None:
    runner = importlib.import_module(
        "scripts.integrations.revise_diffusion_planner_v26_diversified_route_plan"
    )
    args = runner.parse_args(
        [
            "--parent-route-plan",
            "parent.json",
            "--original-qualification-receipt",
            "original/raw_receipt.json",
            "--output-dir",
            "revision-out",
        ]
    )
    assert args.parent_route_plan == Path("parent.json")
    assert args.original_qualification_receipt == Path("original/raw_receipt.json")
