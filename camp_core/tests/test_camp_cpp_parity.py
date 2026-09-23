"""Check exported scorer parity when CAMP_SCORE_EXE names a built C++ example.

The inputs are synthetic contract fixtures, not driving-performance evidence.
"""

import json
import os
from pathlib import Path
import subprocess

import numpy as np
import pytest

from camp_core import dp
from camp_core.integrations.diffusion_planner_v26_camp_reranker import (
    V26_CAMP_ATOM_NAMES,
    build_camp_atom_artifact,
)


@pytest.mark.parametrize("candidate_count", [8, 16, 32])
@pytest.mark.parametrize("mode", ["fixed", "scene"])
def test_exported_cpp_matches_python_for_every_status_head(tmp_path, candidate_count, mode):
    executable = os.environ.get("CAMP_SCORE_EXE")
    if not executable:
        pytest.skip("set CAMP_SCORE_EXE to a built camp_score or camp_installed_score")
    bundle = Path(__file__).resolve().parents[2] / "artifacts/camp_v26_k8_50k"
    selector = dp.load(bundle)
    model = getattr(selector.pipeline, mode)
    checkpoint = "fixed_weight_camp.npz" if mode == "fixed" else "scene_conditioned_camp.npz"
    exported = dp.export_cpp(
        checkpoint=bundle / checkpoint,
        atom_scales=bundle / "atom_scales.json",
        transition_scales=bundle / "transition_scales.json",
        path=tmp_path / "model.json",
        candidate_count=candidate_count,
    )
    payload = json.loads(exported.read_text(encoding="utf-8"))
    rng = np.random.default_rng(20260923)
    ticks, expected = [], []
    for head in payload["patterns"]:
        status = dict(zip(V26_CAMP_ATOM_NAMES, head["status"]))
        raw = rng.uniform(0.0, 12.0, (candidate_count, 16)) * np.asarray(payload["scales"])
        observed = {
            name: raw[:, column]
            for column, name in enumerate(V26_CAMP_ATOM_NAMES)
            if status[name] == "observed"
        }
        artifact = build_camp_atom_artifact(observed, status, candidate_count=candidate_count)
        phi = rng.normal(0.0, 0.1, payload["theta_width"] - 1) if mode == "scene" else None
        expected.append(model.rerank_artifact(artifact, phi))
        tick = {
            "status": head["status"],
            "raw_atoms": [
                [float(value) if head["status"][j] == "observed" else None
                 for j, value in enumerate(row)]
                for row in raw
            ],
        }
        if phi is not None:
            tick["phi"] = phi.tolist()
        ticks.append(tick)
    inputs = tmp_path / "ticks.json"
    inputs.write_text(json.dumps(ticks, allow_nan=False), encoding="utf-8")
    actual = json.loads(subprocess.check_output([executable, str(exported), str(inputs)], text=True))
    assert len(actual) == len(expected) == 24
    for cpp, python in zip(actual, expected):
        assert cpp["selected_row"] == python.selected_row
        np.testing.assert_allclose(cpp["scores"], python.candidate_scores, rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(cpp["active_weights"], python.active_weights, rtol=1e-12, atol=1e-12)
