from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.audit_diffusion_planner_dp_camp_v19_carla_exact_speed_sources import (
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
