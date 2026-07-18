from __future__ import annotations

import copy
import hashlib
import json
import lzma
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_causal_evidence_review import (
    independently_materialize_causal_evidence,
)
from camp_core.integrations.diffusion_planner_v25_causal_evidence_store import (
    ARRAY_CONTRACT,
    LOGICAL_SCHEMA_VERSION,
    SHARD_DIRECTORY,
    externalize_causal_evidence,
    materialize_causal_evidence,
)
from camp_core.integrations.diffusion_planner_v25_snapshot_review import (
    independently_read_snapshot,
)
from camp_core.integrations.diffusion_planner_v25_snapshot_store import (
    SNAPSHOT_SUFFIX,
    encode_snapshot,
)


def _evidence() -> dict:
    rng = np.random.RandomState(25001)
    values = {
        name: np.zeros(shape, dtype=dtype)
        for name, (shape, dtype) in ARRAY_CONTRACT.items()
    }
    time = np.arange(80, dtype=np.float32).reshape(1, 1, 80)
    base = rng.uniform(-20.0, 20.0, (8, 32, 1)).astype(np.float32)
    speed = rng.uniform(-0.15, 0.15, (8, 32, 1)).astype(np.float32)
    phase = rng.uniform(-1.0, 1.0, (8, 32, 1)).astype(np.float32)
    x = base + speed * time
    y = phase + 0.02 * np.sin(time * np.float32(0.05) + phase)
    heading = np.arctan2(
        np.broadcast_to(speed, x.shape), np.ones_like(x)
    ).astype(np.float32)
    predictions = np.stack((x, y, np.cos(heading), np.sin(heading)), axis=-1)
    predictions = np.ascontiguousarray(predictions, dtype=np.float32)
    values["candidate_neighbor_predictions"] = predictions
    values["neighbor_agents_past"] = np.cumsum(
        rng.normal(0.0, 0.02, (32, 31, 11)).astype(np.float32),
        axis=1,
        dtype=np.float32,
    )
    route = np.zeros((25, 20, 33), dtype=np.float32)
    route[..., 0] = np.linspace(0.0, 100.0, 20, dtype=np.float32)
    route[..., 4] = route[..., 0]
    route[..., 6] = route[..., 0]
    route[..., 5] = 2.0
    route[..., 7] = -2.0
    values["route_lanes"] = route
    values["route_lanes_speed_limit"][:] = 13.4
    values["route_lanes_has_speed_limit"][:] = True
    values["ego_shape"][:] = [2.8, 4.8, 2.0]
    return {
        "schema_version": LOGICAL_SCHEMA_VERSION,
        **{name: values[name].tolist() for name in ARRAY_CONTRACT},
    }


def _logical_sha(value: dict) -> str:
    data = (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def test_causal_evidence_shards_are_bit_exact_deterministic_and_independent(
    tmp_path: Path,
) -> None:
    evidence = _evidence()
    first = externalize_causal_evidence(
        output_dir=tmp_path, causal_evidence=evidence
    )
    before = {
        path.name: path.read_bytes()
        for path in (tmp_path / SHARD_DIRECTORY).iterdir()
    }
    second = externalize_causal_evidence(
        output_dir=tmp_path, causal_evidence=copy.deepcopy(evidence)
    )
    after = {
        path.name: path.read_bytes()
        for path in (tmp_path / SHARD_DIRECTORY).iterdir()
    }
    assert first == second
    assert before == after
    assert first["logical_sha256"] == _logical_sha(evidence)
    assert materialize_causal_evidence(
        artifact_root=tmp_path, reference=first
    ) == evidence
    independently_rebuilt, paths = independently_materialize_causal_evidence(
        artifact_root=tmp_path, reference=first
    )
    assert independently_rebuilt == evidence
    assert len(paths) == len(ARRAY_CONTRACT)


def test_causal_evidence_shard_mutations_and_unknown_fields_fail_closed(
    tmp_path: Path,
) -> None:
    evidence = _evidence()
    reference = externalize_causal_evidence(
        output_dir=tmp_path, causal_evidence=evidence
    )
    bad = copy.deepcopy(reference)
    bad["futureOutcome"] = True
    with pytest.raises(ValueError, match="reference schema"):
        independently_materialize_causal_evidence(
            artifact_root=tmp_path, reference=bad
        )

    candidate = reference["arrays"]["candidate_neighbor_predictions"]
    path = tmp_path / candidate["relative_path"]
    original = path.read_bytes()
    path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    with pytest.raises(ValueError, match="storage SHA"):
        independently_materialize_causal_evidence(
            artifact_root=tmp_path, reference=reference
        )


def test_sharded_snapshot_roundtrip_and_full_corpus_storage_budget(
    tmp_path: Path,
) -> None:
    evidence = _evidence()
    reference = externalize_causal_evidence(
        output_dir=tmp_path, causal_evidence=evidence
    )
    payload = {
        "schema_version": "camp_dp_v25_test_snapshot_v1",
        "feature_payload": {
            "causal_evidence": reference,
            "candidate_tensor": np.zeros((8, 80, 4), dtype=np.float32).tolist(),
            "default_output": np.zeros((80, 4), dtype=np.float32).tolist(),
        },
        "sidecar": {"causal_evidence_sha256": _logical_sha(evidence)},
    }
    compressed = encode_snapshot(payload)
    digest = hashlib.sha256(compressed).hexdigest()
    path = tmp_path / f"{digest}{SNAPSHOT_SUFFIX}"
    path.write_bytes(compressed)
    assert independently_read_snapshot(path, digest) == payload

    unique_shards = sum(
        shard.stat().st_size for shard in (tmp_path / SHARD_DIRECTORY).iterdir()
    )
    # One real tick's dynamic evidence plus compressed metadata must remain below
    # 260 KB.  Even without cross-tick static dedup this caps 96,000 train ticks
    # below 25 GB, leaving room for native receipts above the 10 GiB floor.
    assert unique_shards + len(compressed) < 260_000


def test_snapshot_reviewer_rejects_noncanonical_json_inside_valid_xz(
    tmp_path: Path,
) -> None:
    raw = b'{\n  "b": 2,\n  "a": 1\n}\n'
    data = lzma.compress(
        raw, format=lzma.FORMAT_XZ, check=lzma.CHECK_SHA256, preset=6
    )
    digest = hashlib.sha256(data).hexdigest()
    path = tmp_path / f"{digest}{SNAPSHOT_SUFFIX}"
    path.write_bytes(data)
    with pytest.raises(ValueError, match="noncanonical"):
        independently_read_snapshot(path, digest)
