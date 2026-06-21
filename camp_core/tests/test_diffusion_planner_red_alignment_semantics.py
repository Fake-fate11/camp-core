from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_red_alignment_semantics import (
    CURRENT_SUPPORT_STATUS,
    SOURCE_BLOCKED_STATUS,
    UNDERDETERMINED_STATUS,
    analyze,
)


def _source_report(*, ready: bool = True) -> dict:
    return {
        "final_decision": {
            "status": (
                "observable_interaction_payload_attribution_diagnosed"
                if ready
                else "observable_interaction_payload_attribution_source_not_ready"
            ),
            "passed": ready,
        }
    }


def _payload(distances: list[list[float]], alignments: list[list[float]]) -> dict:
    return {
        "observable_state_logging": {
            "candidate_count": len(distances),
            "red_route_point_count": 4,
            "candidate_red_stopline_distance_m": distances,
            "candidate_red_heading_alignment": alignments,
        }
    }


def _write_log(path: Path, records: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_red_alignment_semantics_reports_reverse_sign_underdetermined(
    tmp_path: Path,
) -> None:
    log = _write_log(
        tmp_path / "seed_1" / "camp_selection_log.json",
        [
            _payload(
                [[4.0, 4.5], [8.0, 8.5]],
                [[-0.6, -0.4], [-0.8, -0.7]],
            )
        ],
    )

    report = analyze(
        [log],
        payload_attribution_report=_source_report(),
        label="unit",
        red_distance_budget_m=5.0,
        max_examples=5,
    )

    assert report["final_decision"]["status"] == UNDERDETERMINED_STATUS
    assert report["counts"]["within_budget_candidate_count"] == 1
    assert report["counts"]["reverse_mean_supported_candidate_count"] == 1
    assert report["counts"]["current_mean_supported_candidate_count"] == 0
    assert report["counts"]["records_with_logged_red_geometry"] == 0
    assert report["reason_counts"][
        "reverse_mean_supported_but_geometry_unlogged"
    ] == 1


def test_red_alignment_semantics_detects_current_support(tmp_path: Path) -> None:
    log = _write_log(
        tmp_path / "seed_2" / "camp_selection_log.json",
        [_payload([[3.0, 3.5]], [[0.2, 0.4]])],
    )

    report = analyze(
        [log],
        payload_attribution_report=_source_report(),
        label=None,
        red_distance_budget_m=5.0,
        max_examples=5,
    )

    assert report["final_decision"]["status"] == CURRENT_SUPPORT_STATUS
    assert report["counts"]["current_mean_supported_candidate_count"] == 1
    assert report["counts"]["reverse_mean_supported_candidate_count"] == 0


def test_red_alignment_semantics_source_gate_blocks(tmp_path: Path) -> None:
    log = _write_log(
        tmp_path / "seed_1" / "camp_selection_log.json",
        [_payload([[3.0]], [[0.2]])],
    )

    report = analyze(
        [log],
        payload_attribution_report=_source_report(ready=False),
        label=None,
        red_distance_budget_m=5.0,
        max_examples=5,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["passed"] is False
    assert report["counts"]["scanned_logs"] == 0


def test_red_alignment_semantics_excludes_formal_seed_logs(tmp_path: Path) -> None:
    log = _write_log(
        tmp_path / "seed_11" / "camp_selection_log.json",
        [_payload([[3.0]], [[0.2]])],
    )

    report = analyze(
        [log],
        payload_attribution_report=_source_report(),
        label=None,
        red_distance_budget_m=5.0,
        max_examples=5,
    )

    assert report["counts"]["excluded_formal_seed_logs"] == 1
    assert report["counts"]["scanned_logs"] == 0
    assert report["counts"]["current_mean_supported_candidate_count"] == 0
