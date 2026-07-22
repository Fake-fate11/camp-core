from __future__ import annotations

import copy
import gzip
import hashlib
import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_v25_fresh_storage import (
    CODEC,
    analyze_storage_tree,
    compress_logical_json_file,
    validate_storage_manifest,
    verify_reference_against_source,
)


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode()


def _source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    for index, arm in enumerate(("candidate0", "static14d", "scene14d")):
        run = root / "runs" / f"{index:04d}_{arm}"
        run.mkdir(parents=True)
        (run / "decision_evidence.json").write_bytes(
            _canonical({"arm": arm, "ticks": list(range(64)), "padding": "x" * (100 + index)})
        )
        (run / "terminal.json").write_bytes(_canonical({"complete": True, "tick_count": 64}))
    (root / "report.json").write_bytes(_canonical({"status": "complete"}))
    return root


def test_storage_measurement_is_bit_exact_and_conservative(tmp_path: Path) -> None:
    source = _source(tmp_path)
    retained = "runs/0001_static14d/decision_evidence.json"
    work = tmp_path / "qualification"
    manifest = analyze_storage_tree(
        source,
        work_root=work,
        retained_sample_relpaths=[retained],
        minimum_free_bytes=0,
    )
    reopened = validate_storage_manifest(manifest)
    assert reopened["metrics"]["run_count"] == 3
    assert reopened["metrics"]["projected_1500_arm_upper_bound_nbytes"] > 0
    reference = next(row for row in reopened["references"] if row["relative_path"] == retained)
    assert reference["codec"] == CODEC
    verify_reference_against_source(
        source_root=source, artifact_root=work, reference=reference
    )
    shard = work / reference["retained_regression_shard"]
    assert gzip.decompress(shard.read_bytes()) == (source / retained).read_bytes()

    drifted = copy.deepcopy(manifest)
    drifted["references"][0]["storage_nbytes"] += 1
    with pytest.raises(ValueError):
        validate_storage_manifest(drifted)


def test_new_artifact_logical_compression_preserves_sha(tmp_path: Path) -> None:
    path = tmp_path / "decision_evidence.json"
    raw = _canonical({"ticks": [0, 1, 2], "fresh_b2_opened": False})
    path.write_bytes(raw)
    reference = compress_logical_json_file(path)
    assert not path.exists()
    assert reference["logical_sha256"] == hashlib.sha256(raw).hexdigest()
    assert gzip.decompress((tmp_path / "decision_evidence.json.gz").read_bytes()) == raw
    receipt = json.loads((tmp_path / "decision_evidence.ref.json").read_text())
    assert receipt == reference
