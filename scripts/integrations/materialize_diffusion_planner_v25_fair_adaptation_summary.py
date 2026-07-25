"""Materialize the additive V25 fair-pool adaptation summary.

This path reads only the already sealed validation report and numeric
preimages.  It never imports or invokes the model, pool generator, selector,
or closed-loop runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
import sys

for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_fair_adaptation_summary import (  # noqa: E402
    SCHEMA_VERSION,
    build_summary,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_ROOT = "29688aa7ff4eb5edf43ca2379063f45228faedea80a7a3245e07aba297cc9dfd"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()


def _tracked_changes(repo: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=no"],
            cwd=repo,
            text=True,
        ).strip()
    )


def materialize(
    *,
    source: Path,
    source_root: str,
    output: Path,
    fixed_dp_repo: Path,
) -> str:
    source = source.resolve()
    if source_root != SOURCE_ROOT:
        raise ValueError("source validation root is not the accepted hard-stop root")
    source_seal = verify_complete_seal(
        source, source_root, label="fair nonholdout validation"
    )
    expected_inventory = {
        "HEADS.json",
        "replay_preimages.npz",
        "report.json",
        "run.exit",
    }
    if set(source_seal["manifest_paths"]) != expected_inventory:
        raise ValueError("source validation inventory drifted")
    fixed_dp_repo = fixed_dp_repo.resolve()
    if (
        _git_head(fixed_dp_repo) != FIXED_DP_HEAD
        or _tracked_changes(fixed_dp_repo)
    ):
        raise ValueError("fixed DP authority drifted")
    report = json.loads((source / "report.json").read_text("utf-8"))
    with np.load(source / "replay_preimages.npz", allow_pickle=False) as archive:
        arrays = {name: np.array(archive[name], copy=True) for name in archive.files}
    summary = build_summary(report, arrays)
    if summary["schema_version"] != SCHEMA_VERSION:
        raise AssertionError("summary schema drifted")
    implementation_head = _git_head(ROOT)
    artifact = {
        "schema_version": (
            "camp_dp_v25_fair_nonholdout_adaptation_summary_artifact_v1"
        ),
        "status": "passed_additive_adaptation_summary_hard_stop_preserved",
        "implementation_head": implementation_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "source": {
            "path": str(source),
            "root_sha256": source_root,
            "report_sha256": _sha256_file(source / "report.json"),
            "replay_preimages_sha256": _sha256_file(
                source / "replay_preimages.npz"
            ),
        },
        "summary": summary,
        "boundaries": {
            "source_files_read": ["report.json", "replay_preimages.npz"],
            "model_pool_selector_or_closed_loop_invoked": False,
            "fresh_or_holdout_accessed": False,
            "fresh_or_b4_raw_outcome_read": False,
            "old_artifact_or_cas_written": False,
            "training_or_retraining_executed": False,
            "threshold_or_scientific_contract_modified": False,
            "hard_stop_preserved": True,
            "confirmatory_effect_claim_authorized": False,
            "ultra_submission_authorized": False,
        },
    }
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent)
    )
    try:
        (staging / "report.json").write_bytes(_canonical_bytes(artifact))
        (staging / "HEADS.json").write_bytes(
            _canonical_bytes(
                {
                    "implementation_head": implementation_head,
                    "fixed_dp_head": FIXED_DP_HEAD,
                    "source_validation_root_sha256": source_root,
                }
            )
        )
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(staging, label="V25 fair adaptation summary")
        os.replace(staging, output)
        verify_complete_seal(output, root, label="V25 fair adaptation summary")
        return root
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    args = parser.parse_args()
    print(materialize(**vars(args)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
