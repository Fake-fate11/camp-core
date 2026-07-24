from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_fresh_execution_review import (
    _independent_candidate_tensor_preimages,
    _independent_decision_evidence_indices,
)
from scripts.integrations.run_diffusion_planner_v25_holdout_execution import (
    _candidate_tensor_preimage_sink,
    _expected_decision_evidence_indices,
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


@pytest.mark.parametrize(
    "arm,evaluation_arm,sample_every,expected",
    [
        ("candidate0_operational_default", "candidate0", 5, []),
        ("camp_static14d", "static14d", 5, list(range(0, 64, 5))),
        ("camp_scene14d_no_v2i", "scene14d", 1, list(range(64))),
        ("camp_static14d", "static14d", 64, [0]),
    ],
)
def test_decision_evidence_cadence_matches_producer_and_independent_review(
    arm: str,
    evaluation_arm: str,
    sample_every: int,
    expected: list[int],
) -> None:
    config = {
        "protocol": {
            "holdout_plan_arm": arm,
            "sample_every_ticks": sample_every,
        }
    }
    assert _expected_decision_evidence_indices(config) == expected
    assert (
        _independent_decision_evidence_indices(
            config, evaluation_arm=evaluation_arm
        )
        == expected
    )


@pytest.mark.parametrize("sample_every", [False, 0, -1, 1.5, "5"])
def test_decision_evidence_cadence_type_drift_fails_closed(
    sample_every: object,
) -> None:
    config = {
        "protocol": {
            "holdout_plan_arm": "camp_static14d",
            "sample_every_ticks": sample_every,
        }
    }
    with pytest.raises(ValueError, match="sampling cadence"):
        _expected_decision_evidence_indices(config)
    with pytest.raises(ValueError, match="sampling cadence"):
        _independent_decision_evidence_indices(
            config, evaluation_arm="static14d"
        )
