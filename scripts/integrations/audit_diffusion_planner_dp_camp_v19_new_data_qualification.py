#!/usr/bin/env python3
"""Fail-closed v19 WOMD/Waymax and CARLA new-data qualification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
BASELINE_NAME = "DP-default deterministic/MAP baseline"
NEXT_WORK_TARGET = (
    "user_decision_required_before_carla_large_download_additional_disk_"
    "and_license_source_preflight"
)
DOWNLOAD_WORK_TARGET = "v19_carla_0_9_16_official_linux_package_download_only"
CLAIMS = {
    "performance_claim": "no_claim",
    "bounded_offline_safety_proxy_improvement": "supported",
    "closed_loop_safety_claim": "not_yet_supported",
    "broad_CAMP_over_native_DP_Top1_claim": "not_supported",
}


def _known_true(value: Any) -> bool:
    return value is True


def _qualify(name: str, source: dict[str, Any]) -> dict[str, Any]:
    exact_window = (
        source.get("history_seconds") == 3
        and source.get("evaluation_seconds") == 8
    )
    gates = {
        "exact_3s_plus_8s": exact_window,
        "official_route_speed_source_contract": _known_true(
            source.get("speed_source_contract")
        ),
        "topology_actors_signals": _known_true(
            source.get("topology_actors_signals")
        ),
        "fixed_dp_k8": _known_true(source.get("fixed_dp_compatible")),
        "official_closed_loop_metrics": _known_true(
            source.get("closed_loop_metrics")
        ),
        "license_sample_disk": _known_true(
            source.get("license_accepted_and_minimal_sample_available")
        ),
    }
    reasons = []
    if not exact_window:
        reasons.append("frozen exact 3s history plus 8s evaluation is unavailable")
    if not gates["official_route_speed_source_contract"]:
        reasons.append("official route speed source contract is unproven")
    if not gates["fixed_dp_k8"]:
        reasons.append("unchanged fixed-DP K=8 compatibility is unproven")
    return {
        "name": name,
        "gates": gates,
        "qualified": all(gates.values()),
        "first_failure": next(
            (key for key, passed in gates.items() if not passed), None
        ),
        "reasons": "; ".join(reasons),
    }


def build_report(evidence: dict[str, Any]) -> dict[str, Any]:
    if evidence.get("dp_head") != FIXED_DP_HEAD:
        raise ValueError("fixed DP HEAD drift")
    free_bytes = int(evidence["free_bytes"])
    floor_bytes = int(evidence["floor_bytes"])
    archive_bytes = int(evidence["carla"]["compressed_archive_bytes"])
    headroom = max(free_bytes - floor_bytes, 0)
    extracted_bytes = int(evidence["carla"].get("extracted_upper_bound_bytes", 0))
    overhead_bytes = int(
        evidence["carla"].get("extraction_overhead_reserve_bytes", 0)
    )
    peak_bytes = archive_bytes + extracted_bytes + overhead_bytes

    womd_source = dict(evidence["womd"])
    womd_source["speed_source_contract"] = False
    womd = _qualify("WOMD + Waymax", womd_source)

    carla_source = dict(evidence["carla"])
    carla_source["license_accepted_and_minimal_sample_available"] = bool(
        carla_source.get("license_accepted_and_minimal_sample_available")
        and peak_bytes <= headroom
    )
    carla = _qualify("CARLA synthetic fallback", carla_source)
    carla["disk"] = {
        "free_bytes": free_bytes,
        "floor_bytes": floor_bytes,
        "headroom_bytes": headroom,
        "compressed_archive_bytes": archive_bytes,
        "compressed_archive_deficit_bytes": max(archive_bytes - headroom, 0),
        "extracted_upper_bound_bytes": extracted_bytes,
        "extraction_overhead_reserve_bytes": overhead_bytes,
        "peak_bytes": peak_bytes,
        "projected_free_after_peak_bytes": free_bytes - peak_bytes,
    }

    return {
        "schema_version": "dp_camp_v19_new_data_qualification_v1",
        "heads": {"camp": evidence["camp_head"], "fixed_dp": evidence["dp_head"]},
        "baseline_name": BASELINE_NAME,
        "native_ranked_top1": False,
        "claim_taxonomy": dict(CLAIMS),
        "sources": {"womd_waymax": womd, "carla": carla},
        "data_access": {
            "large_download": False,
            "sample_download": False,
            "simulator_executed": False,
            "metrics_computed": False,
            "holdout_accessed": False,
        },
        "decision": (
            {
                "status": "v19_carla_license_source_disk_preflight_passed_download_ready",
                "next_work_target": DOWNLOAD_WORK_TARGET,
            }
            if carla["qualified"]
            else {
                "status": "v19_new_data_qualification_failed_closed_before_download",
                "next_work_target": NEXT_WORK_TARGET,
            }
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    womd = report["sources"]["womd_waymax"]
    carla = report["sources"]["carla"]
    disk = carla["disk"]
    return "\n".join(
        [
            "# V19 New-Data Qualification",
            "",
            "No data or simulator was downloaded or executed.",
            "",
            f"- WOMD/Waymax qualified: `{womd['qualified']}`; first failure: "
            f"`{womd['first_failure']}`.",
            f"- CARLA qualified: `{carla['qualified']}`; first failure: "
            f"`{carla['first_failure']}`.",
            f"- CARLA compressed bytes: `{disk['compressed_archive_bytes']}`.",
            f"- Floor-preserving headroom: `{disk['headroom_bytes']}`.",
            f"- Deficit before extraction: "
            f"`{disk['compressed_archive_deficit_bytes']}`.",
            f"- Next work target: `{report['decision']['next_work_target']}`.",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report(json.loads(args.input.read_text(encoding="utf-8")))
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
