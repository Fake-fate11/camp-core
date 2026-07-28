from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _module():
    path = ROOT / "scripts/integrations/run_diffusion_planner_v26_nuplan_mini_b8_smoke.py"
    spec = importlib.util.spec_from_file_location("v26_nuplan_mini_b8_smoke", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_smoke_parser_requires_only_the_active_mode_inputs(tmp_path: Path) -> None:
    module = _module()
    adapter = module.parse_args(
        [
            "--mode",
            "adapter",
            "--data-root",
            str(tmp_path / "dataset"),
            "--db-file",
            str(tmp_path / "mini.db"),
            "--output-root",
            str(tmp_path / "adapter"),
        ]
    )
    assert adapter.mode == "adapter"
    assert adapter.fixed_dp_repo is None


def test_same_pool_selector_tie_is_deterministic_without_row_mutation() -> None:
    module = _module()
    scores = np.array([3.0, 1.0, 1.0, 2.0, 9.0, 8.0, 7.0, 6.0])
    mask = np.array([True, True, True, False, False, False, False, False])
    rows = [f"row-{index}" for index in range(8)]
    before_scores = scores.copy()
    before_mask = mask.copy()

    receipt = module._select(scores, mask, rows)

    assert receipt == {
        "status": "ok",
        "selected_index": 1,
        "selected_row_sha256": "row-1",
        "candidate_pool_sha256": None,
        "mask_count": 3,
        "margin": 0.0,
        "tie_indices": [1, 2],
    }
    assert np.array_equal(scores, before_scores)
    assert np.array_equal(mask, before_mask)


def test_pre_forward_status_receipt_has_zero_execution_counts() -> None:
    module = _module()
    assert module._status("running", "scenario_builder") == {
        "schema": module.SCHEMA,
        "status": "running",
        "reason": "scenario_builder",
        "model_calls": 0,
        "dp_calls": 0,
        "gpu_calls": 0,
    }
