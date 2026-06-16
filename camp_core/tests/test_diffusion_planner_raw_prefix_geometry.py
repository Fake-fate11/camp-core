from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_raw_prefix_geometry import (
    analyze,
    render_markdown,
)


def _prefix(end_x: float, end_y: float, *, dim4: bool = False) -> list[list[float]]:
    rows = []
    for step in range(4):
        ratio = float(step + 1) / 4.0
        if dim4:
            rows.append([end_x * ratio, end_y * ratio, 1.0, 0.0])
        else:
            rows.append([end_x * ratio, end_y * ratio, 0.0])
    return rows


def _record() -> dict:
    return {
        "num_candidates": 3,
        "selected_index": 0,
        "candidate_raw_trajectory_prefix": [
            _prefix(4.0, 0.0, dim4=True),
            _prefix(4.0, 1.0, dim4=True),
            _prefix(4.0, -1.0, dim4=True),
        ],
        "candidate_perfect_tracker_postprocessed_reference_prefix": [
            _prefix(4.0, 0.0),
            _prefix(4.0, 0.1),
            _prefix(4.0, -0.1),
        ],
    }


def _write_log(tmp_path, records: list[dict]):
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_raw_prefix_geometry_reports_postprocess_compression(tmp_path) -> None:
    report = analyze([_write_log(tmp_path, [_record()])], label="unit")

    assert report["records"]["total"] == 1
    assert report["summary"]["prefix_steps"]["mean"] == pytest.approx(4.0)
    assert report["summary"]["endpoint_pairwise_mean_ratio"]["mean"] == pytest.approx(
        0.1
    )
    assert report["summary"]["endpoint_pairwise_mean_delta_m"]["mean"] == pytest.approx(
        -1.2
    )
    assert report["summary"]["prefix_pairwise_mean_ratio"]["mean"] == pytest.approx(
        0.1
    )
    assert report["summary"]["prefix_pairwise_mean_delta_m"]["mean"] == pytest.approx(
        -0.75
    )
    assert report["summary"]["selected_distance_mean_ratio"]["mean"] == pytest.approx(
        0.1
    )
    assert report["summary"]["raw_to_post_max_m"]["mean"] == pytest.approx(0.9)
    assert report["rates"]["endpoint_pairwise_mean_compression_rate"] == 1.0
    assert report["rates"]["prefix_pairwise_mean_compression_rate"] == 1.0
    assert not report["analysis"]["uses_outcome_labels"]

    markdown = render_markdown(report)
    assert "Raw Prefix Geometry Audit" in markdown
    assert "endpoint_pairwise_mean_ratio" in markdown


def test_raw_prefix_geometry_rejects_missing_raw_prefix(tmp_path) -> None:
    record = _record()
    record.pop("candidate_raw_trajectory_prefix")

    with pytest.raises(ValueError, match="candidate_raw_trajectory_prefix"):
        analyze([_write_log(tmp_path, [record])], label="unit")


def test_raw_prefix_geometry_clamps_to_common_horizon(tmp_path) -> None:
    record = _record()
    record["candidate_raw_trajectory_prefix"] = [
        _prefix(4.0, 0.0, dim4=True)[:3],
        _prefix(4.0, 1.0, dim4=True)[:3],
        _prefix(4.0, -1.0, dim4=True)[:3],
    ]

    report = analyze([_write_log(tmp_path, [record])], label="unit")

    assert report["summary"]["prefix_steps"]["mean"] == pytest.approx(3.0)
