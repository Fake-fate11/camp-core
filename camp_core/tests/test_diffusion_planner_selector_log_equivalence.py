from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.integrations.compare_diffusion_planner_selector_logs import (
    compare_selector_log_roots,
)


def _record() -> dict:
    return {
        "selected_index": 1,
        "feasible_mask": [True, True],
        "infeasibility_reasons": [[], []],
        "used_fallback": False,
        "camp_fallback_mode": "uniform",
        "atom_schema_version": "dp_camp_v8_12d",
        "atom_names": ["a", "b"],
        "scores": [1.0, 0.5],
        "selection_scores": [1.0, 0.5],
        "weights": [0.5, 0.5],
        "selection_weights": [0.5, 0.5],
        "atoms": [[1.0, 1.0], [0.5, 0.5]],
        "normalized_atoms": [[1.0, 1.0], [0.5, 0.5]],
        "selection_normalized_atoms": [[1.0, 1.0], [0.5, 0.5]],
    }


def _write_log(root: Path, record: dict, subdir: str = "route/run") -> None:
    output = root / subdir / "camp_selection_log.json"
    output.parent.mkdir(parents=True)
    output.write_text(json.dumps([record]), encoding="utf-8")


def test_selector_log_equivalence_accepts_roundoff_within_tolerance(
    tmp_path: Path,
) -> None:
    baseline = _record()
    candidate = deepcopy(baseline)
    candidate["atoms"][1][1] += 4e-16
    _write_log(tmp_path / "baseline", baseline)
    _write_log(tmp_path / "candidate", candidate)

    report = compare_selector_log_roots(
        tmp_path / "baseline",
        tmp_path / "candidate",
        atol=1e-15,
        rtol=1e-15,
    )

    assert report["equivalent"]
    assert report["paired_logs"] == 1
    assert report["records"] == 1
    assert report["numeric_field_mismatches"]["atoms"] == 0
    assert report["numeric_nonexact_entries"]["atoms"] == 1
    assert report["numeric_max_abs_diff"]["atoms"] == pytest.approx(4e-16)


def test_selector_log_equivalence_rejects_decision_change(tmp_path: Path) -> None:
    baseline = _record()
    candidate = deepcopy(baseline)
    candidate["selected_index"] = 0
    _write_log(tmp_path / "baseline", baseline)
    _write_log(tmp_path / "candidate", candidate)

    report = compare_selector_log_roots(
        tmp_path / "baseline",
        tmp_path / "candidate",
    )

    assert not report["equivalent"]
    assert report["exact_field_mismatches"]["selected_index"] == 1


def test_selector_log_equivalence_requires_strict_pairing(tmp_path: Path) -> None:
    _write_log(tmp_path / "baseline", _record(), "route/run")
    _write_log(tmp_path / "candidate", _record(), "other/run")

    with pytest.raises(ValueError, match="pairing mismatch"):
        compare_selector_log_roots(
            tmp_path / "baseline",
            tmp_path / "candidate",
        )
