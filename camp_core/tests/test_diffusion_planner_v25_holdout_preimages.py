from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_fresh_execution_review import (
    _independent_candidate_tensor_preimages,
)
from scripts.integrations.run_diffusion_planner_v25_holdout_execution import (
    _candidate_tensor_preimage_sink,
    _seal_candidate_tensor_preimages,
)


def _valid_candidates() -> np.ndarray:
    value = np.zeros((8, 80, 4), dtype=np.float32)
    value[..., 2] = np.float32(1.0)
    return value


def test_candidate_tensor_preimage_is_reopened_before_projection(
    tmp_path: Path,
) -> None:
    root = tmp_path / "preimages"
    sink = _candidate_tensor_preimage_sink(root)
    candidates = _valid_candidates()
    digest = hashlib.sha256(candidates.tobytes(order="C")).hexdigest()
    for tick_index in range(64):
        sink(
            tick_index,
            candidates,
            {"candidate_tensor_sha256": digest},
        )
    _seal_candidate_tensor_preimages(root, expected_tick_count=64)
    raw_ticks = [
        {"candidate_tensor_sha256_before": digest} for _ in range(64)
    ]
    _independent_candidate_tensor_preimages(root, raw_ticks=raw_ticks)


def test_candidate_tensor_preimage_mutation_fails_independent_review(
    tmp_path: Path,
) -> None:
    root = tmp_path / "preimages"
    sink = _candidate_tensor_preimage_sink(root)
    candidates = _valid_candidates()
    digest = hashlib.sha256(candidates.tobytes(order="C")).hexdigest()
    for tick_index in range(64):
        sink(
            tick_index,
            candidates,
            {"candidate_tensor_sha256": digest},
        )
    _seal_candidate_tensor_preimages(root, expected_tick_count=64)
    path = root / "tick_63.float32.bin"
    raw = bytearray(path.read_bytes())
    raw[0] ^= 1
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="preimage receipt drifted"):
        _independent_candidate_tensor_preimages(
            root,
            raw_ticks=[
                {"candidate_tensor_sha256_before": digest}
                for _ in range(64)
            ],
        )


def test_candidate0_primary_forbids_online_k8_preimage(tmp_path: Path) -> None:
    _seal_candidate_tensor_preimages(
        tmp_path / "absent", expected_tick_count=0
    )
    present = tmp_path / "present"
    present.mkdir()
    with pytest.raises(ValueError, match="candidate0 primary"):
        _seal_candidate_tensor_preimages(present, expected_tick_count=0)
