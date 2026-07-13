from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.carla_exact_speed_source import (
    LaneSurfaceSample,
    LiftingTolerances,
    RouteLiftingContext,
    canonical_json_sha256,
    lift_k8_route_receipt,
    route_identity_directions,
)
from camp_core.integrations.diffusion_planner_v19_nuplan_bridge import array_sha256
from scripts.integrations.audit_diffusion_planner_dp_camp_v19_carla_exact_speed_sources import (
    build_lifted_report,
    build_report,
)


XODR = """<OpenDRIVE>
<road id="1" junction="-1"><type s="0"><speed max="10" unit="m/s"/></type><lanes><laneSection s="0"><left><lane id="1" type="driving"/></left></laneSection></lanes></road>
<road id="2" junction="9"><link><predecessor elementType="road" elementId="1"/><successor elementType="road" elementId="3"/></link><lanes><laneSection s="0"><left><lane id="1" type="driving"/></left></laneSection></lanes></road>
<road id="3" junction="-1"><type s="0"><speed max="10" unit="m/s"/></type><lanes><laneSection s="0"><left><lane id="1" type="driving"/></left></laneSection></lanes></road>
<junction id="9"><connection id="0" incomingRoad="1" connectingRoad="2"/></junction>
</OpenDRIVE>"""


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    xodr = tmp_path / "TownTest.xodr"
    xodr.write_text(XODR, encoding="utf-8")
    candidates = tmp_path / "candidates.json"
    candidates.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "record_id": "record-1",
                        "dp_default_index": 0,
                        "candidates": [
                            [
                                {
                                    "road_id": "1",
                                    "section_id": 0,
                                    "lane_id": 1,
                                    "s": 1.0,
                                    "is_junction": False,
                                }
                            ],
                            [
                                {
                                    "road_id": "2",
                                    "section_id": 0,
                                    "lane_id": 1,
                                    "s": 1.0,
                                    "is_junction": True,
                                }
                            ],
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return xodr, candidates


def test_report_keeps_masks_reasons_and_dp_default_eligibility(tmp_path: Path) -> None:
    xodr, candidates = _write_inputs(tmp_path)

    report = build_report(xodr, candidates, "B", None)

    assert report["outcome_reads"] == 0
    assert report["eligible_record_count"] == 1
    assert report["records"][0]["candidate_source_eligible_mask"] == [True, False]
    assert report["records"][0]["dp_default_source_eligible"] is True
    assert report["records"][0]["reasons"][1].endswith(
        "junction_not_allowed_by_rung_b"
    )
    assert report == build_report(xodr, candidates, "B", None)


def test_report_rejects_outcome_or_label_fields(tmp_path: Path) -> None:
    xodr, candidates = _write_inputs(tmp_path)
    payload = json.loads(candidates.read_text(encoding="utf-8"))
    payload["records"][0]["collision_outcome"] = False
    candidates.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="forbidden outcome field"):
        build_report(xodr, candidates, "C", None)


class _Map:
    def get_waypoint_xodr(self, road_id: int, lane_id: int, s: float):
        return type(
            "Waypoint",
            (),
            {
                "road_id": road_id,
                "section_id": 0,
                "lane_id": lane_id,
                "s": s,
                "is_junction": False,
                "transform": type(
                    "Transform",
                    (),
                    {"location": type("Location", (), {"z": 3.5})()},
                )(),
            },
        )()


def _lifting_context() -> RouteLiftingContext:
    samples = tuple(
        LaneSurfaceSample("1", 0, 1, float(i), float(i), 0.0, 3.5, 4.0, False)
        for i in range(81)
    )
    return RouteLiftingContext(
        samples=samples,
        edges=(),
        identity_directions=route_identity_directions(samples, 1e-6),
        route_sample_step_m=1.0,
        tolerances=LiftingTolerances(1e-6, 1e-6, 1e-6, 1e-6),
        map_sha256="a" * 64,
        source_sha256="b" * 64,
        route_graph_sha256="c" * 64,
    )


def _lifting_receipt(
    *,
    candidate0_bad: bool = False,
    all_bad: bool = False,
    only_candidate0: bool = False,
):
    base = np.zeros((80, 4), dtype=np.float32)
    base[:, 0] = np.arange(80, dtype=np.float32)
    candidates = np.repeat(base[None, :, :], 8, axis=0)
    if all_bad:
        candidates[:, :, 1] = np.float32(10.0)
    else:
        candidates[1, :, 1] = np.float32(10.0)
        candidates[2, 40:, 0] = candidates[2, 39::-1, 0]
        if candidate0_bad:
            candidates[0, :, 1] = np.float32(10.0)
        elif only_candidate0:
            candidates[1:, :, 1] = np.float32(10.0)
    operational = candidates[0].copy()
    receipt = lift_k8_route_receipt(
        candidates=candidates,
        operational_top1=operational,
        agents_from_world_tf=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        context=_lifting_context(),
        map_api=_Map(),
        candidate_tensor_sha256=array_sha256(candidates),
        operational_top1_sha256=array_sha256(operational),
        provenance={"record_id": "record-1", "native_ranked_top1": False},
    )
    _reseal_tick(receipt)
    return receipt


def _write_lifting_inputs(tmp_path: Path, receipt=None) -> tuple[Path, Path]:
    xodr = tmp_path / "TownTest.xodr"
    xodr.write_text(XODR, encoding="utf-8")
    lifting = tmp_path / "lifting.json"
    lifting.write_text(
        json.dumps({"records": [receipt or _lifting_receipt()]}, sort_keys=True),
        encoding="utf-8",
    )
    return xodr, lifting


def _reseal_tick(receipt: dict) -> None:
    payload = dict(receipt)
    payload.pop("lifting_receipt_sha256", None)
    receipt["lifting_receipt_sha256"] = canonical_json_sha256(payload)


def test_lifted_report_intersects_lifting_and_speed_masks(tmp_path: Path) -> None:
    xodr, lifting = _write_lifting_inputs(tmp_path)

    report = build_lifted_report(xodr, lifting, "B", None)
    row = report["records"][0]

    assert row["candidate_lifting_eligible_mask"] == [
        True,
        False,
        False,
        True,
        True,
        True,
        True,
        True,
    ]
    assert row["candidate_source_eligible_mask"] == row[
        "candidate_lifting_eligible_mask"
    ]
    assert row["dp_operational_top1_source_complete"] is True
    assert row["candidate0_operational_top1_equivalent"] is True
    assert row["record_source_eligible"] is True
    assert report["outcome_reads"] == 0
    assert report["metric_calls"] == 0


def test_lifted_report_blocks_paired_support_with_only_candidate0(tmp_path) -> None:
    receipt = _lifting_receipt(only_candidate0=True)
    xodr, lifting = _write_lifting_inputs(tmp_path, receipt)

    row = build_lifted_report(xodr, lifting, "B", None)["records"][0]

    assert row["record_source_eligible"] is True
    assert row["source_complete_candidate_count"] == 1
    assert row["paired_source_support_eligible"] is False
    assert row["paired_source_support_reason"] == (
        "fewer_than_two_source_complete_candidates"
    )


def test_lifted_report_rejects_tampered_root_or_candidate_sha(tmp_path: Path) -> None:
    receipt = _lifting_receipt()
    receipt["provenance"]["record_id"] = "tampered"
    xodr, lifting = _write_lifting_inputs(tmp_path, receipt)
    with pytest.raises(ValueError, match="lifting receipt SHA"):
        build_lifted_report(xodr, lifting, "B", None)

    receipt = _lifting_receipt()
    receipt["candidate_tensor_sha256"] = "0" * 64
    _reseal_tick(receipt)
    lifting.write_text(json.dumps({"records": [receipt]}), encoding="utf-8")
    with pytest.raises(ValueError, match="candidate tensor SHA"):
        build_lifted_report(xodr, lifting, "B", None)

    receipt = _lifting_receipt()
    for field in (
        "candidate_tensor_sha256",
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
    ):
        receipt[field] = "bad"
    _reseal_tick(receipt)
    lifting.write_text(json.dumps({"records": [receipt]}), encoding="utf-8")
    with pytest.raises(ValueError, match="candidate tensor SHA"):
        build_lifted_report(xodr, lifting, "B", None)


def test_lifted_report_rejects_missing_point_receipt(tmp_path: Path) -> None:
    receipt = _lifting_receipt()
    receipt["candidate_receipts"][3]["points"].pop()
    _reseal_tick(receipt)
    xodr, lifting = _write_lifting_inputs(tmp_path, receipt)

    with pytest.raises(ValueError, match="80 point receipts"):
        build_lifted_report(xodr, lifting, "B", None)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("source_complete_candidate_count", 0, "source-complete candidate count"),
        ("paired_source_support_eligible", False, "paired source support eligibility"),
        (
            "paired_source_support_reason",
            "fewer_than_two_source_complete_candidates",
            "paired source support reason",
        ),
    ],
)
def test_lifted_report_rejects_resealed_paired_support_tampering(
    tmp_path: Path, field: str, value: object, match: str
) -> None:
    receipt = _lifting_receipt()
    receipt[field] = value
    _reseal_tick(receipt)
    xodr, lifting = _write_lifting_inputs(tmp_path, receipt)

    with pytest.raises(ValueError, match=match):
        build_lifted_report(xodr, lifting, "B", None)


def test_lifted_report_rejects_resealed_selected_index_tampering(
    tmp_path: Path,
) -> None:
    receipt = _lifting_receipt()
    receipt["selected_index"] = 0
    _reseal_tick(receipt)
    xodr, lifting = _write_lifting_inputs(tmp_path, receipt)

    with pytest.raises(ValueError, match="selected index"):
        build_lifted_report(xodr, lifting, "B", None)


def test_lifted_report_rejects_resealed_boolean_candidate_count(
    tmp_path: Path,
) -> None:
    receipt = _lifting_receipt(only_candidate0=True)
    receipt["source_complete_candidate_count"] = True
    _reseal_tick(receipt)
    xodr, lifting = _write_lifting_inputs(tmp_path, receipt)

    with pytest.raises(ValueError, match="source-complete candidate count"):
        build_lifted_report(xodr, lifting, "B", None)


def test_lifted_report_fails_closed_on_operational_lifting_mismatch(
    tmp_path: Path,
) -> None:
    receipt = _lifting_receipt()
    operational = receipt["operational_top1_receipt"]
    operational["points"][0]["z"] = 4.0
    trajectory = [
        {key: value for key, value in point.items() if key != "candidate_index"}
        for point in operational["points"]
    ]
    operational["trajectory_lifting_sha256"] = canonical_json_sha256(trajectory)
    receipt["candidate0_operational_top1_equivalent"] = False
    receipt["record_source_eligible"] = False
    receipt["reason"] = "candidate0_operational_top1_mismatch"
    receipt["paired_source_support_eligible"] = False
    receipt["paired_source_support_reason"] = "candidate0_operational_top1_mismatch"
    _reseal_tick(receipt)
    xodr, lifting = _write_lifting_inputs(tmp_path, receipt)

    row = build_lifted_report(xodr, lifting, "B", None)["records"][0]

    assert row["candidate0_operational_top1_equivalent"] is False
    assert row["record_source_eligible"] is False


def test_lifted_report_recomputes_paired_support_after_speed_exclusion(
    tmp_path: Path,
) -> None:
    receipt = _lifting_receipt()
    for candidate in receipt["candidate_receipts"][3:]:
        for point in candidate["points"]:
            point["road_id"] = "2"
        trajectory = [
            {key: value for key, value in point.items() if key != "candidate_index"}
            for point in candidate["points"]
        ]
        candidate["trajectory_lifting_sha256"] = canonical_json_sha256(trajectory)
    _reseal_tick(receipt)
    xodr, lifting = _write_lifting_inputs(tmp_path, receipt)

    row = build_lifted_report(xodr, lifting, "B", None)["records"][0]

    assert sum(row["candidate_lifting_eligible_mask"]) >= 2
    assert row["candidate_source_eligible_mask"] == [
        True,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
    ]
    assert row["source_complete_candidate_count"] == 1
    assert row["paired_source_support_eligible"] is False
    assert row["paired_source_support_reason"] == (
        "fewer_than_two_source_complete_candidates"
    )


@pytest.mark.parametrize(
    ("candidate0_bad", "all_bad", "reason", "count"),
    [
        (True, False, "candidate0_source_incomplete", 5),
        (False, True, "all_k_source_ineligible", 0),
    ],
)
def test_lifted_report_retains_fail_closed_masks(
    tmp_path: Path,
    candidate0_bad: bool,
    all_bad: bool,
    reason: str,
    count: int,
) -> None:
    receipt = _lifting_receipt(candidate0_bad=candidate0_bad, all_bad=all_bad)
    xodr, lifting = _write_lifting_inputs(tmp_path, receipt)

    row = build_lifted_report(xodr, lifting, "B", None)["records"][0]

    assert row["record_source_eligible"] is False
    assert row["reason"] == reason
    assert row["source_complete_candidate_count"] == count
    assert row["paired_source_support_eligible"] is False
    assert row["paired_source_support_reason"] == reason
    assert len(row["candidate_source_eligible_mask"]) == 8
    assert len(row["candidate_source_reasons"]) == 8


def test_lifted_report_rejects_forbidden_outcome_fields(tmp_path: Path) -> None:
    receipt = _lifting_receipt()
    receipt["safety_metric"] = 0.0
    xodr, lifting = _write_lifting_inputs(tmp_path, receipt)

    with pytest.raises(ValueError, match="forbidden outcome field"):
        build_lifted_report(xodr, lifting, "B", None)
