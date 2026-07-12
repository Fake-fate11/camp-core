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
    candidate_source_mask,
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
    values: Dict[SegmentKey, Tuple[float, ...]] = {}
    for key, speeds in raw.get("segment_values_mps", {}).items():
        road, section, lane = key.split("|", 2)
        values[(road, int(section), int(lane))] = tuple(float(x) for x in speeds)
    return values


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
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--rung", choices=("A", "B", "C"), required=True)
    parser.add_argument("--actor-observations", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report(
        args.xodr, args.candidates, args.rung, args.actor_observations
    )
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
