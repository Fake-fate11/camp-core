#!/usr/bin/env python3
"""Source-only CARLA exact-speed ladder census."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from camp_core.integrations.carla_exact_speed_source import (  # noqa: E402
    SegmentKey,
    SegmentRef,
    _paired_source_support,
    _reject_forbidden_receipt_fields,
    _tick_failure_reason,
    candidate_source_mask,
    canonical_json_sha256,
    parse_opendrive_speed_index,
)


_FORBIDDEN_FIELD_PARTS = (
    "outcome",
    "label",
    "collision",
    "safetycost",
    "metric",
    "latency",
    "ade",
    "fde",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_sha256(value: Any, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValueError("%s SHA is invalid" % name)


def _reject_outcome_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in _FORBIDDEN_FIELD_PARTS):
                raise ValueError("forbidden outcome field: %s" % key)
            _reject_outcome_fields(child)
    elif isinstance(value, list):
        for child in value:
            _reject_outcome_fields(child)


def _segment(raw: Mapping[str, Any]) -> SegmentRef:
    if not isinstance(raw.get("is_junction"), bool):
        raise ValueError("is_junction must be boolean")
    return SegmentRef(
        road_id=str(raw["road_id"]),
        section_id=int(raw["section_id"]),
        lane_id=int(raw["lane_id"]),
        s=float(raw["s"]),
        is_junction=raw["is_junction"],
    )


def _actor_values(path: Optional[Path]) -> Dict[SegmentKey, Tuple[float, ...]]:
    if path is None:
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    _reject_outcome_fields(raw)
    values: Dict[SegmentKey, Tuple[float, ...]] = {}
    for key, speeds in raw.get("segment_values_mps", {}).items():
        road, section, lane = key.split("|", 2)
        values[(road, int(section), int(lane))] = tuple(float(x) for x in speeds)
    return values


def _validate_lifting_decision(
    decision: Mapping[str, Any], candidate_index: int
) -> None:
    points = decision.get("points")
    if not isinstance(points, list) or len(points) != 80:
        raise ValueError("candidate must retain exactly 80 point receipts")
    for point_index, point in enumerate(points):
        if not isinstance(point, dict):
            raise ValueError("point receipt must be an object")
        if point.get("candidate_index") != candidate_index:
            raise ValueError("point candidate index mismatch")
        if point.get("point_index") != point_index:
            raise ValueError("point receipt index mismatch")
    trajectory = [
        {key: value for key, value in point.items() if key != "candidate_index"}
        for point in points
    ]
    if decision.get("trajectory_lifting_sha256") != canonical_json_sha256(
        trajectory
    ):
        raise ValueError("trajectory lifting SHA mismatch")
    failures = [point.get("reason") for point in points if point.get("reason") != "lifted"]
    eligible = not failures
    if decision.get("eligible") is not eligible:
        raise ValueError("candidate lifting eligibility mismatch")
    expected_reason = "source_complete" if eligible else failures[0]
    if decision.get("reason") != expected_reason:
        raise ValueError("candidate lifting reason mismatch")
    if eligible:
        for point in points:
            if not (
                point.get("unique_identity") is True
                and point.get("unique_station") is True
                and point.get("topology_continuous") is True
            ):
                raise ValueError("eligible point receipt is incomplete")
            if any(
                point.get(key) is None
                for key in ("road_id", "section_id", "lane_id", "s", "z")
            ):
                raise ValueError("eligible point segment receipt is incomplete")


def _validate_lifting_receipt(receipt: Mapping[str, Any]) -> None:
    payload = dict(receipt)
    sealed = payload.pop("lifting_receipt_sha256", None)
    if sealed != canonical_json_sha256(payload):
        raise ValueError("lifting receipt SHA mismatch")
    if "selected_index" not in receipt or receipt["selected_index"] is not None:
        raise ValueError("selected index must be None")
    for field, name in (
        ("candidate_tensor_sha256", "candidate tensor"),
        ("candidate_tensor_sha256_before", "candidate tensor"),
        ("candidate_tensor_sha256_after", "candidate tensor"),
        ("candidate0_sha256", "candidate 0"),
        ("operational_top1_sha256", "operational Top-1"),
        ("operational_top1_sha256_before", "operational Top-1"),
        ("operational_top1_sha256_after", "operational Top-1"),
        ("map_sha256", "map"),
        ("source_sha256", "source"),
        ("route_graph_sha256", "route graph"),
    ):
        _require_sha256(receipt.get(field), name)
    provenance = receipt.get("provenance")
    if not isinstance(provenance, Mapping):
        raise ValueError("lifting receipt provenance is missing")
    _reject_forbidden_receipt_fields(provenance)
    _require_sha256(provenance.get("capture_sha256"), "capture provenance")
    _require_sha256(
        provenance.get("lifting_corridor_sha256"), "lifting corridor provenance"
    )
    candidates = receipt.get("candidate_receipts")
    if not isinstance(candidates, list) or len(candidates) != 8:
        raise ValueError("lifting receipt must contain eight candidates")
    for index, decision in enumerate(candidates):
        if not isinstance(decision, dict):
            raise ValueError("candidate lifting receipt must be an object")
        _validate_lifting_decision(decision, index)
    operational = receipt.get("operational_top1_receipt")
    if not isinstance(operational, dict):
        raise ValueError("operational Top-1 receipt is missing")
    _validate_lifting_decision(operational, 0)

    mask = [bool(decision["eligible"]) for decision in candidates]
    reasons = [str(decision["reason"]) for decision in candidates]
    if receipt.get("candidate_source_eligible_mask") != mask:
        raise ValueError("candidate lifting mask mismatch")
    if receipt.get("candidate_source_reasons") != reasons:
        raise ValueError("candidate lifting reasons mismatch")
    if receipt.get("candidate_tensor_sha256") != receipt.get(
        "candidate_tensor_sha256_before"
    ) or receipt.get("candidate_tensor_sha256") != receipt.get(
        "candidate_tensor_sha256_after"
    ):
        raise ValueError("candidate tensor SHA mismatch")
    if receipt.get("operational_top1_sha256") != receipt.get(
        "operational_top1_sha256_before"
    ) or receipt.get("operational_top1_sha256") != receipt.get(
        "operational_top1_sha256_after"
    ):
        raise ValueError("operational Top-1 SHA mismatch")
    raw_equivalent = receipt["candidate0_sha256"] == receipt[
        "operational_top1_sha256"
    ]
    equivalent = raw_equivalent and (
        candidates[0]["trajectory_lifting_sha256"]
        == operational["trajectory_lifting_sha256"]
    )
    if receipt.get("candidate0_operational_top1_equivalent") is not equivalent:
        if not raw_equivalent:
            raise ValueError("candidate 0 raw SHA equivalence evidence mismatch")
        raise ValueError("operational Top-1 equivalence evidence mismatch")
    if receipt.get("dp_operational_top1_source_complete") is not bool(
        operational["eligible"]
    ):
        raise ValueError("operational Top-1 completeness mismatch")
    reason = _tick_failure_reason(
        mask=mask,
        candidate0_complete=bool(candidates[0]["eligible"]),
        operational_complete=bool(operational["eligible"]),
        equivalent=equivalent,
        candidate_expected=receipt["candidate_tensor_sha256"],
        candidate_before=receipt["candidate_tensor_sha256_before"],
        candidate_after=receipt["candidate_tensor_sha256_after"],
        operational_expected=receipt["operational_top1_sha256"],
        operational_before=receipt["operational_top1_sha256_before"],
        operational_after=receipt["operational_top1_sha256_after"],
    )
    if receipt.get("reason") != reason or receipt.get("record_source_eligible") is not (
        reason == "source_complete"
    ):
        raise ValueError("lifting record eligibility mismatch")
    source_complete_candidate_count = sum(bool(item) for item in mask)
    paired_source_support_eligible, paired_source_support_reason = (
        _paired_source_support(reason, mask)
    )
    recorded_candidate_count = receipt.get("source_complete_candidate_count")
    if (
        type(recorded_candidate_count) is not int
        or recorded_candidate_count != source_complete_candidate_count
    ):
        raise ValueError("source-complete candidate count mismatch")
    if receipt.get("paired_source_support_eligible") is not paired_source_support_eligible:
        raise ValueError("paired source support eligibility mismatch")
    if receipt.get("paired_source_support_reason") != paired_source_support_reason:
        raise ValueError("paired source support reason mismatch")


def _segments_from_lifting(
    decision: Mapping[str, Any], index: Any
) -> list[SegmentRef]:
    segments = []
    for point in decision["points"]:
        road_id = str(point["road_id"])
        road = index.roads.get(road_id)
        if road is None:
            raise ValueError("lifted road is missing from OpenDRIVE")
        segments.append(
            SegmentRef(
                road_id=road_id,
                section_id=int(point["section_id"]),
                lane_id=int(point["lane_id"]),
                s=float(point["s"]),
                is_junction=road.junction_id is not None,
            )
        )
    return segments


def _lifted_record(
    receipt: Mapping[str, Any], index: Any, actors: Mapping[SegmentKey, Tuple[float, ...]], rung: str
) -> Dict[str, Any]:
    candidates = receipt["candidate_receipts"]
    lifting_mask = [bool(decision["eligible"]) for decision in candidates]
    speed_decisions = [
        candidate_source_mask(_segments_from_lifting(decision, index), index, actors, rung)
        if decision["eligible"]
        else None
        for decision in candidates
    ]
    speed_mask = [decision is not None and decision.eligible for decision in speed_decisions]
    source_mask = [lifted and speed for lifted, speed in zip(lifting_mask, speed_mask)]
    source_reasons = [
        decision.reason if decision is not None else "lifting:%s" % candidates[i]["reason"]
        for i, decision in enumerate(speed_decisions)
    ]
    operational = receipt["operational_top1_receipt"]
    operational_speed = (
        candidate_source_mask(
            _segments_from_lifting(operational, index), index, actors, rung
        )
        if operational["eligible"]
        else None
    )
    operational_complete = bool(
        operational["eligible"]
        and operational_speed is not None
        and operational_speed.eligible
    )
    equivalent = bool(receipt["candidate0_operational_top1_equivalent"])
    if not any(source_mask):
        reason = "all_k_source_ineligible"
    elif not source_mask[0]:
        reason = "candidate0_source_incomplete"
    elif not operational_complete:
        reason = "dp_operational_top1_source_incomplete"
    elif not equivalent:
        reason = "candidate0_operational_top1_mismatch"
    else:
        reason = "source_complete"
    source_complete_candidate_count = sum(bool(item) for item in source_mask)
    paired_source_support_eligible, paired_source_support_reason = (
        _paired_source_support(reason, source_mask)
    )
    return {
        "record_id": str(receipt.get("provenance", {}).get("record_id", "")),
        "candidate_lifting_eligible_mask": lifting_mask,
        "candidate_speed_eligible_mask": speed_mask,
        "candidate_source_eligible_mask": source_mask,
        "candidate_lifting_reasons": [str(item["reason"]) for item in candidates],
        "candidate_source_reasons": source_reasons,
        "candidate_point_failure_reasons": [
            [
                {"point_index": point["point_index"], "reason": point["reason"]}
                for point in item["points"]
                if point["reason"] != "lifted"
            ]
            for item in candidates
        ],
        "dp_operational_top1_source_complete": operational_complete,
        "candidate0_operational_top1_equivalent": equivalent,
        "record_source_eligible": reason == "source_complete",
        "reason": reason,
        "source_complete_candidate_count": source_complete_candidate_count,
        "paired_source_support_eligible": paired_source_support_eligible,
        "paired_source_support_reason": paired_source_support_reason,
    }


def build_lifted_report(
    xodr_path: Path,
    lifting_receipt_path: Path,
    rung: str,
    actor_observations_path: Optional[Path],
) -> Dict[str, Any]:
    payload = json.loads(lifting_receipt_path.read_text(encoding="utf-8"))
    _reject_outcome_fields(payload)
    records_raw = payload.get("records")
    if not isinstance(records_raw, list):
        raise ValueError("lifting receipt records are missing")
    for receipt in records_raw:
        if not isinstance(receipt, dict):
            raise ValueError("lifting receipt record must be an object")
        _validate_lifting_receipt(receipt)
    index = parse_opendrive_speed_index(xodr_path.read_text(encoding="utf-8"))
    actors = _actor_values(actor_observations_path)
    records = [_lifted_record(receipt, index, actors, rung) for receipt in records_raw]
    return {
        "rung": rung,
        "xodr_sha256": _sha256(xodr_path),
        "lifting_receipt_input_sha256": _sha256(lifting_receipt_path),
        "actor_observations_sha256": (
            _sha256(actor_observations_path)
            if actor_observations_path is not None
            else None
        ),
        "record_count": len(records),
        "eligible_record_count": sum(row["record_source_eligible"] for row in records),
        "paired_source_support_record_count": sum(
            row["paired_source_support_eligible"] for row in records
        ),
        "all_k_ineligible_record_count": sum(
            not any(row["candidate_source_eligible_mask"]) for row in records
        ),
        "coverage_breakdown": {
            "lifting_ineligible_candidates": sum(
                mask is False
                for row in records
                for mask in row["candidate_lifting_eligible_mask"]
            ),
            "speed_ineligible_candidates": sum(
                mask is False
                for row in records
                for mask in row["candidate_speed_eligible_mask"]
            ),
            "source_eligible_candidates": sum(
                mask is True
                for row in records
                for mask in row["candidate_source_eligible_mask"]
            ),
        },
        "records": records,
        "outcome_reads": 0,
        "simulator_outcome_calls": 0,
        "metric_calls": 0,
        "fallback_used": False,
    }


def build_report(
    xodr_path: Path,
    candidate_path: Path,
    rung: str,
    actor_observations_path: Optional[Path],
) -> Dict[str, Any]:
    payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    _reject_outcome_fields(payload)
    index = parse_opendrive_speed_index(xodr_path.read_text(encoding="utf-8"))
    actors = _actor_values(actor_observations_path)
    records = []
    eligible_records = 0
    all_k_ineligible = 0
    for raw_record in payload.get("records", []):
        decisions = [
            candidate_source_mask(
                [_segment(segment) for segment in candidate], index, actors, rung
            )
            for candidate in raw_record["candidates"]
        ]
        mask = [decision.eligible for decision in decisions]
        default_index = int(raw_record["dp_default_index"])
        if default_index < 0 or default_index >= len(mask):
            raise ValueError("dp_default_index out of range")
        default_eligible = mask[default_index]
        record_eligible = default_eligible and any(mask)
        eligible_records += int(record_eligible)
        all_k_ineligible += int(not any(mask))
        records.append(
            {
                "record_id": str(raw_record["record_id"]),
                "candidate_source_eligible_mask": mask,
                "reasons": [decision.reason for decision in decisions],
                "dp_default_index": default_index,
                "dp_default_source_eligible": default_eligible,
                "record_source_eligible": record_eligible,
            }
        )
    return {
        "rung": rung,
        "xodr_sha256": _sha256(xodr_path),
        "candidate_input_sha256": _sha256(candidate_path),
        "actor_observations_sha256": (
            _sha256(actor_observations_path)
            if actor_observations_path is not None
            else None
        ),
        "record_count": len(records),
        "eligible_record_count": eligible_records,
        "all_k_ineligible_record_count": all_k_ineligible,
        "records": records,
        "outcome_reads": 0,
        "simulator_outcome_calls": 0,
        "metric_calls": 0,
        "fallback_used": False,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xodr", type=Path, required=True)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--candidates", type=Path)
    inputs.add_argument("--lifting-receipts", type=Path)
    parser.add_argument("--rung", choices=("A", "B", "C"), required=True)
    parser.add_argument("--actor-observations", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = (
        build_lifted_report(
            args.xodr, args.lifting_receipts, args.rung, args.actor_observations
        )
        if args.lifting_receipts is not None
        else build_report(args.xodr, args.candidates, args.rung, args.actor_observations)
    )
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
