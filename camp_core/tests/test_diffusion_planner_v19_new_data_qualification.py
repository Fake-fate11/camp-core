from __future__ import annotations

import importlib


def _module():
    return importlib.import_module(
        "scripts.integrations."
        "audit_diffusion_planner_dp_camp_v19_new_data_qualification"
    )


def _evidence() -> dict:
    return {
        "camp_head": "a" * 40,
        "dp_head": "7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "free_bytes": 15_041_548_288,
        "floor_bytes": 10 * 1024**3,
        "womd": {
            "speed_schema": True,
            "topology_actors_signals": True,
            "history_seconds": 1,
            "evaluation_seconds": 8,
            "fixed_dp_compatible": None,
            "closed_loop_metrics": True,
            "license_accepted_and_minimal_sample_available": False,
        },
        "carla": {
            "speed_schema": True,
            "topology_actors_signals": True,
            "history_seconds": 3,
            "evaluation_seconds": 8,
            "fixed_dp_compatible": None,
            "closed_loop_metrics": True,
            "license_accepted_and_minimal_sample_available": True,
            "compressed_archive_bytes": 8_346_095_504,
        },
    }


def test_womd_fails_frozen_three_plus_eight_contract() -> None:
    report = _module().build_report(_evidence())

    assert report["sources"]["womd_waymax"]["gates"]["exact_3s_plus_8s"] is False
    assert report["sources"]["womd_waymax"]["qualified"] is False
    assert report["sources"]["womd_waymax"]["first_failure"] == "exact_3s_plus_8s"


def test_carla_fails_before_download_when_floor_headroom_is_too_small() -> None:
    report = _module().build_report(_evidence())
    carla = report["sources"]["carla"]

    assert carla["disk"]["headroom_bytes"] == 4_304_130_048
    assert carla["disk"]["compressed_archive_deficit_bytes"] == 4_041_965_456
    assert carla["gates"]["license_sample_disk"] is False
    assert carla["qualified"] is False


def test_unknown_gate_fails_closed() -> None:
    report = _module().build_report(_evidence())

    assert report["sources"]["carla"]["gates"]["fixed_dp_k8"] is False
    assert "unproven" in report["sources"]["carla"]["reasons"]


def test_claims_and_baseline_remain_frozen() -> None:
    report = _module().build_report(_evidence())

    assert report["baseline_name"] == "DP-default deterministic/MAP baseline"
    assert report["native_ranked_top1"] is False
    assert report["claim_taxonomy"] == {
        "performance_claim": "no_claim",
        "bounded_offline_safety_proxy_improvement": "supported",
        "closed_loop_safety_claim": "not_yet_supported",
        "broad_CAMP_over_native_DP_Top1_claim": "not_supported",
    }
    assert report["decision"]["next_work_target"] == (
        "user_decision_required_before_carla_large_download_additional_disk_"
        "and_license_source_preflight"
    )


def test_carla_preflight_passes_with_proven_sources_and_peak_headroom() -> None:
    evidence = _evidence()
    evidence["free_bytes"] = 79_465_508_864
    evidence["carla"].update(
        {
            "speed_source_contract": True,
            "fixed_dp_compatible": True,
            "extracted_upper_bound_bytes": 31 * 1024**3,
            "extraction_overhead_reserve_bytes": 2 * 1024**3,
        }
    )

    report = _module().build_report(evidence)
    carla = report["sources"]["carla"]

    assert carla["qualified"] is True
    assert carla["gates"]["official_route_speed_source_contract"] is True
    assert carla["disk"]["projected_free_after_peak_bytes"] == 35_685_933_168
    assert report["decision"] == {
        "status": "v19_carla_license_source_disk_preflight_passed_download_ready",
        "next_work_target": "v19_carla_0_9_16_official_linux_package_download_only",
    }
