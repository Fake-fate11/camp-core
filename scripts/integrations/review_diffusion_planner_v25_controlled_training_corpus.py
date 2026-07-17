#!/usr/bin/env python3
"""Independently validate a sealed V25 corrected 1500-identity corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (  # noqa: E402
    CORPUS_STEPS,
    EXPECTED_EXECUTABLE_IDENTITIES,
    SCHEMA_VERSION as EXECUTION_SCHEMA_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
    _git_head,
    _tracked_dirty,
)


SCHEMA_VERSION = "camp_dp_v25_controlled_training_corpus_review_v1"


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"expected JSONL objects: {path}")
        rows.append(value)
    return rows


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def review(corpus: Path, expected_root: str) -> dict[str, Any]:
    head = _git_head(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree is dirty")
    seal = verify_complete_seal(corpus, expected_root, label="V25 corrected corpus")
    report = _json(corpus / "report.json")
    progress = _json(corpus / "progress.json")
    results = _jsonl(corpus / "results.jsonl")
    index = _jsonl(corpus / "snapshot_index.jsonl")
    if (
        (corpus / "run.exit").read_text(encoding="ascii") != "0\n"
        or report.get("schema_version") != EXECUTION_SCHEMA_VERSION
        or report.get("status") != "passed"
        or report.get("mode") != "execute"
        or report.get("camp_head") != head
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("attempted_identity_count") != EXPECTED_EXECUTABLE_IDENTITIES
        or report.get("retained_identity_count") != EXPECTED_EXECUTABLE_IDENTITIES
        or len(results) != EXPECTED_EXECUTABLE_IDENTITIES
        or progress.get("status") != "complete"
        or progress.get("completed") != EXPECTED_EXECUTABLE_IDENTITIES
        or progress.get("total") != EXPECTED_EXECUTABLE_IDENTITIES
        or report.get("fresh_b_opened") is not False
        or report.get("training_snapshot_outcome_fields") != []
        or report.get("selector_training_executed") is not False
        or report.get("calibration_executed") is not False
    ):
        raise ValueError("corrected corpus terminal report contract drifted")
    seen_results: set[str] = set()
    expected_snapshots = 0
    for ordinal, row in enumerate(results):
        scenario_id = row.get("scenario_id")
        status = row.get("status")
        count = row.get("snapshot_count")
        if (
            row.get("ordinal") != ordinal
            or not isinstance(scenario_id, str)
            or len(scenario_id) != 64
            or scenario_id in seen_results
            or row.get("retained") is not True
            or row.get("fresh_b_opened") is not False
            or row.get("outcome_fields_consumed") != []
        ):
            raise ValueError("corpus result denominator drifted")
        if status == "complete":
            if count != CORPUS_STEPS or row.get("capability_failure") is not None:
                raise ValueError("complete corpus identity is not exactly 64 ticks")
            expected_snapshots += CORPUS_STEPS
        elif status == "failed":
            failure = row.get("capability_failure")
            if (
                count != 0
                or row.get("failure_type") != "RetainedScenarioCapabilityFailure"
                or not isinstance(failure, Mapping)
                or failure.get("scenario_id") != scenario_id
                or failure.get("family") != row.get("family")
            ):
                raise ValueError("failed corpus identity is not a typed retained failure")
        else:
            raise ValueError("corpus identity has an illegal terminal status")
        seen_results.add(scenario_id)
    if (
        len(index) != expected_snapshots
        or report.get("snapshot_count") != expected_snapshots
        or progress.get("snapshot_count") != expected_snapshots
    ):
        raise ValueError("corpus snapshot denominator is inconsistent")
    seen_ticks: set[tuple[str, int]] = set()
    for row in index:
        key = (str(row.get("scenario_id")), row.get("tick_index"))
        relative = row.get("relative_path")
        if (
            key in seen_ticks
            or key[0] not in seen_results
            or isinstance(key[1], bool)
            or not isinstance(key[1], int)
            or not 0 <= key[1] < CORPUS_STEPS
            or not isinstance(relative, str)
            or not relative.startswith("snapshots/")
            or ".." in Path(relative).parts
        ):
            raise ValueError("snapshot index authority is invalid")
        path = corpus / relative
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        snapshot = json.loads(data)
        features = snapshot.get("feature_payload", {})
        sidecar = snapshot.get("sidecar", {})
        source = np.asarray(features.get("atom_source_valid_mask"))
        applicable = np.asarray(features.get("atom_applicable_mask"))
        physical = features.get("physical_feasible_mask")
        atoms = np.asarray(features.get("atom_matrix"), dtype=np.float64)
        candidates = np.asarray(features.get("candidate_tensor"), dtype=np.float32)
        default = np.asarray(features.get("default_output"), dtype=np.float32)
        candidate_rows = (
            [
                hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()
                for value in candidates
            ]
            if candidates.ndim == 3 and candidates.shape[0] == 8
            else []
        )
        tensor_sha = (
            hashlib.sha256(np.ascontiguousarray(candidates).tobytes()).hexdigest()
            if candidate_rows
            else None
        )
        default_sha = (
            hashlib.sha256(np.ascontiguousarray(default).tobytes()).hexdigest()
            if default.shape == (80, 4)
            else None
        )
        selected = sidecar.get("selected_index")
        if (
            row.get("sha256") != digest
            or path.name != f"{digest}.json"
            or snapshot.get("schema_version") != SNAPSHOT_SCHEMA_VERSION
            or sidecar.get("scenario_id") != key[0]
            or sidecar.get("tick_index") != key[1]
            or source.dtype != np.bool_
            or applicable.dtype != np.bool_
            or source.shape != (8, 14)
            or applicable.shape != (8, 14)
            or np.any(applicable & ~source)
            or atoms.shape != (8, 14)
            or not np.isfinite(atoms).all()
            or np.any(atoms < 0.0)
            or candidates.shape != (8, 80, 4)
            or default.shape != (80, 4)
            or features.get("candidate_row_sha256") != candidate_rows
            or sidecar.get("candidate_tensor_sha256_before") != tensor_sha
            or sidecar.get("candidate_tensor_sha256_after") != tensor_sha
            or sidecar.get("default_output_sha256") != default_sha
            or sidecar.get("candidate0_sha256") != candidate_rows[0]
            or not np.array_equal(default, candidates[0])
            or isinstance(selected, bool)
            or not isinstance(selected, int)
            or not 0 <= selected < 8
            or sidecar.get("selected_trajectory_sha256")
            != candidate_rows[selected]
            or not isinstance(physical, list)
            or len(physical) != 8
            or any(not isinstance(value, bool) for value in physical)
            or sidecar.get("fresh_b_opened") is not False
            or sidecar.get("outcome_fields_consumed") != []
        ):
            raise ValueError("snapshot schema/source/hash contract drifted")
        seen_ticks.add(key)
    for row in results:
        if row["status"] == "complete":
            keys = {key[1] for key in seen_ticks if key[0] == row["scenario_id"]}
            if keys != set(range(CORPUS_STEPS)):
                raise ValueError("complete identity has missing or duplicate tick index")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_full_corpus_review",
        "review_head": head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(corpus),
        "reviewed_root_sha256": seal["root_sha256"],
        "identity_denominator": len(results),
        "complete_identity_count": sum(row["status"] == "complete" for row in results),
        "typed_retained_failure_count": sum(row["status"] == "failed" for row in results),
        "snapshot_count": expected_snapshots,
        "partial_snapshot_count": 0,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-artifact", type=Path, required=True)
    parser.add_argument("--corpus-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        report = review(args.corpus_artifact, args.corpus_root_sha256)
        _write(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_text(
            f"camp_head={report['review_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(
            " ".join(sys.argv) + "\n", encoding="utf-8"
        )
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        root = seal_artifact(args.output_dir, label="V25 corrected corpus review")
        print(json.dumps({"status": report["status"], "root_sha256": root}))
    except BaseException as exc:
        _write(
            args.output_dir / "failure.json",
            {"schema_version": SCHEMA_VERSION, "status": "failed", "reason": str(exc)},
        )
        (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
        seal_artifact(args.output_dir, label="V25 failed corrected corpus review")
        raise


if __name__ == "__main__":
    main()
