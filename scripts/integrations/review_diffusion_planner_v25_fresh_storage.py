#!/usr/bin/env python3
"""Independently review V25 Fresh B2 logical storage and capacity authority."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)


SCHEMA_VERSION = "camp_dp_v25_fresh_storage_qualification_review_v1"
QUALIFICATION_SCHEMA = "camp_dp_v25_fresh_storage_qualification_artifact_v1"
MANIFEST_SCHEMA = "camp_dp_v25_fresh_artifact_storage_qualification_v1"
REFERENCE_SCHEMA = "camp_dp_v25_fresh_logical_file_reference_v1"
CODEC = "gzip_rfc1952_level6_mtime0"
MINIMUM_FREE = 10 * 1024**3
RESERVE = 1024**3
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def review(
    *, artifact: Path, root_sha256: str, output_dir: Path
) -> str:
    source = artifact.resolve()
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    seal = verify_complete_seal(source, root_sha256, label="Fresh storage qualification")
    if (source / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh storage qualification did not pass")
    report = _json_object(source / "report.json")
    manifest = _json_object(source / "storage_manifest.json")
    if (
        report.get("schema_version") != QUALIFICATION_SCHEMA
        or report.get("status") != "passed_fresh_storage_equivalence_and_capacity"
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("capacity_gate_passed") is not True
        or report.get("fresh_b2_opened") is not False
        or report.get("outcome_fields_consumed") != []
        or manifest.get("schema_version") != MANIFEST_SCHEMA
        or manifest.get("fresh_b2_opened") is not False
        or manifest.get("outcome_fields_consumed") != []
    ):
        raise ValueError("Fresh storage qualification authority drifted")
    raw_root = Path(report["calibration_artifact"]).resolve()
    verify_complete_seal(
        raw_root,
        report["calibration_root_sha256"],
        label="immutable calibration storage source",
    )
    if (raw_root / "run.exit").read_bytes() != b"1\n":
        raise ValueError("calibration storage source exit drifted")
    refs = manifest.get("references")
    if type(refs) is not list or not refs:
        raise ValueError("Fresh storage references are missing")
    inventory = _files(raw_root)
    expected_paths = [path.relative_to(raw_root).as_posix() for path in inventory]
    actual_paths = [row.get("relative_path") for row in refs]
    if actual_paths != expected_paths:
        raise ValueError("Fresh storage source inventory drifted")
    checked: list[dict[str, Any]] = []
    for path, row in zip(inventory, refs, strict=True):
        checked.append(_review_reference(path, row, artifact_root=source))
    logical_root = _sha_bytes(
        _canonical_bytes(
            [
                {"relative_path": row["relative_path"], "logical_sha256": row["logical_sha256"], "logical_nbytes": row["logical_nbytes"]}
                for row in checked
            ]
        )
    )
    metrics = _metrics(checked)
    if (
        manifest.get("logical_tree_sha256") != logical_root
        or not _strict_equal(manifest.get("metrics"), metrics)
        or report.get("logical_tree_sha256") != logical_root
        or report.get("storage_manifest_sha256") != _sha_file(source / "storage_manifest.json")[0]
        or report.get("projected_1500_arm_upper_bound_nbytes")
        != metrics["projected_1500_arm_upper_bound_nbytes"]
        or metrics["projected_1500_arm_upper_bound_nbytes"]
        > report.get("fresh_incremental_budget_bytes")
    ):
        raise ValueError("Fresh storage logical root, metrics, or capacity drifted")
    output.mkdir(parents=True)
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_fresh_storage_equivalence_and_capacity_review",
        "camp_head": _git_head(ROOT),
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(source),
        "reviewed_root_sha256": seal["root_sha256"],
        "source_file_count": len(checked),
        "source_run_count": metrics["run_count"],
        "logical_tree_sha256": logical_root,
        "logical_bytes_independently_reconstructed": True,
        "retained_sample_shards_independently_decompressed": True,
        "projected_1500_arm_upper_bound_nbytes": metrics[
            "projected_1500_arm_upper_bound_nbytes"
        ],
        "fresh_incremental_budget_bytes": report["fresh_incremental_budget_bytes"],
        "capacity_gate_passed": True,
        "original_calibration_artifact_modified": False,
        "preopen_dp_forward_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    _write_json(output / "report.json", result)
    (output / "HEADS").write_text(
        f"camp_head={result['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n", encoding="ascii"
    )
    (output / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output / "run.exit").write_text("0\n", encoding="ascii")
    return seal_artifact(output, label="V25 Fresh storage qualification review")


def _review_reference(path: Path, row: Mapping[str, Any], *, artifact_root: Path) -> dict[str, Any]:
    fields = {"schema_version", "relative_path", "codec", "logical_sha256", "logical_nbytes", "storage_sha256", "storage_nbytes", "retained_regression_shard"}
    if type(row) is not dict or set(row) != fields or row.get("schema_version") != REFERENCE_SCHEMA:
        raise ValueError("Fresh storage reference schema drifted")
    logical_sha, logical_size = _sha_file(path)
    if row.get("logical_sha256") != logical_sha or row.get("logical_nbytes") != logical_size:
        raise ValueError("Fresh storage logical source drifted")
    if row.get("codec") == "identity":
        if row.get("storage_sha256") != logical_sha or row.get("storage_nbytes") != logical_size or row.get("retained_regression_shard") is not None:
            raise ValueError("Fresh storage identity reference drifted")
    elif row.get("codec") == CODEC:
        storage_sha, storage_size = _independent_gzip_digest(path)
        if row.get("storage_sha256") != storage_sha or row.get("storage_nbytes") != storage_size:
            raise ValueError("Fresh storage gzip bytes drifted")
        retained = row.get("retained_regression_shard")
        if retained is not None:
            shard = (artifact_root / retained).resolve()
            if artifact_root not in shard.parents or shard.is_symlink() or not shard.is_file():
                raise ValueError("Fresh storage retained shard is unsafe")
            if _sha_file(shard) != (storage_sha, storage_size):
                raise ValueError("Fresh storage retained shard bytes drifted")
            digest = hashlib.sha256()
            count = 0
            with gzip.open(shard, "rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
                    count += len(chunk)
            if digest.hexdigest() != logical_sha or count != logical_size:
                raise ValueError("Fresh storage retained shard reconstruction drifted")
    else:
        raise ValueError("Fresh storage codec drifted")
    return dict(row)


class _DigestWriter:
    def __init__(self) -> None:
        self.digest = hashlib.sha256()
        self.count = 0

    def write(self, value: bytes) -> int:
        self.digest.update(value)
        self.count += len(value)
        return len(value)

    def flush(self) -> None:
        return None


def _independent_gzip_digest(path: Path) -> tuple[str, int]:
    sink = _DigestWriter()
    with path.open("rb") as source:
        with gzip.GzipFile(filename="", mode="wb", fileobj=sink, compresslevel=6, mtime=0) as target:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                target.write(chunk)
    return sink.digest.hexdigest(), sink.count


def _metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    run_bytes: dict[str, int] = {}
    top = 0
    for row in rows:
        parts = Path(row["relative_path"]).parts
        if len(parts) >= 3 and parts[0] == "runs":
            run_bytes[parts[1]] = run_bytes.get(parts[1], 0) + row["storage_nbytes"]
        else:
            top += row["storage_nbytes"]
    values = sorted(run_bytes.values())
    if len(values) != 300:
        raise ValueError("Fresh storage calibration run denominator drifted")
    gzip_rows = [row for row in rows if row["codec"] == CODEC]
    gzip_values = [row["storage_nbytes"] for row in gzip_rows]
    if len(gzip_values) != 300:
        raise ValueError("Fresh storage decision-evidence denominator drifted")
    maximum = values[-1]
    writer_peak = max(row["logical_nbytes"] + row["storage_nbytes"] for row in gzip_rows)
    projected = maximum * 1500 + top * 5 + writer_peak + RESERVE
    return {
        "run_count": len(values),
        "logical_nbytes": sum(row["logical_nbytes"] for row in rows),
        "measured_storage_nbytes": sum(row["storage_nbytes"] for row in rows),
        "decision_evidence_logical_nbytes": sum(row["logical_nbytes"] for row in rows if row["codec"] == CODEC),
        "decision_evidence_storage_nbytes": sum(gzip_values),
        "run_storage_mean_nbytes": float(sum(values) / len(values)),
        "run_storage_p95_nbytes": sorted(values)[math.ceil(0.95 * len(values)) - 1],
        "run_storage_max_nbytes": maximum,
        "top_level_storage_nbytes": top,
        "writer_temporary_peak_nbytes": writer_peak,
        "seal_and_review_reserve_nbytes": RESERVE,
        "projected_1500_arm_upper_bound_nbytes": projected,
        "projection_policy": "1500_times_observed_max_arm_plus_5_times_top_level_plus_raw_and_gzip_writer_peak_plus_1GiB_seal_review",
        "fresh_arm_count": 1500,
    }


def _files(root: Path) -> list[Path]:
    base = root.resolve()
    values: list[Path] = []
    for current, directories, names in os.walk(base, followlinks=False):
        current_path = Path(current)
        if any((current_path / name).is_symlink() for name in directories):
            raise ValueError("Fresh storage source directory symlink")
        for name in names:
            path = current_path / name
            if path.is_symlink() or not path.is_file() or base not in path.resolve().parents:
                raise ValueError("Fresh storage source path is unsafe")
            values.append(path.resolve())
    return sorted(values, key=lambda path: path.relative_to(base).as_posix())


def _json_object(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates, parse_constant=_bad_constant)
    if type(value) is not dict or raw != _canonical_bytes(value):
        raise ValueError(f"noncanonical authority JSON: {path}")
    return value


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _bad_constant(value: str) -> Any:
    raise ValueError(value)


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _sha_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            count += len(chunk)
    return digest.hexdigest(), count


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git_head(path: Path) -> str:
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(_strict_equal(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(_strict_equal(a, b) for a, b in zip(left, right, strict=True))
    return bool(left == right)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = review(**vars(args))
    print(json.dumps({"status": "sealed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
