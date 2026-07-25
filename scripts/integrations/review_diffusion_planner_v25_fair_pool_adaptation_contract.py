"""Seal an independent literal review of the fair-pool adaptation contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_fair_pool_adaptation_review import (  # noqa: E402
    EXPECTED_FIXED_DP,
    review_contract_literal,
)


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def review(
    *,
    source: Path,
    source_root: str,
    output: Path,
    fixed_dp_repo: Path,
) -> str:
    source = source.resolve()
    verify_complete_seal(source, source_root, label="fair-pool contract")
    if (
        _git_head(fixed_dp_repo) != EXPECTED_FIXED_DP
        or _tracked(fixed_dp_repo)
    ):
        raise ValueError("fixed DP authority drifted")
    source_report = json.loads((source / "report.json").read_text("utf-8"))
    contract_bytes = (source / "contract.json").read_bytes()
    contract = json.loads(contract_bytes)
    literal = review_contract_literal(contract)
    if (
        source_report.get("status") != "sealed_outcome_independent_design_only"
        or source_report.get("contract") != contract
        or source_report.get("acquisition_authorized") is not False
        or source_report.get("fresh_or_b4_outcome_read") is not False
        or source_report.get("claim_authorized") is not False
    ):
        raise ValueError("source artifact boundary drifted")
    zero_fields = [
        "calibration_run_count",
        "repeat_model_run_count",
        "pool_run_count",
        "selector_run_count",
        "closed_loop_run_count",
        "fresh_run_count",
        "holdout_run_count",
        "training_run_count",
    ]
    if any(source_report.get(field) != 0 for field in zero_fields):
        raise ValueError("source artifact records prohibited run")
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent)
    )
    try:
        report = {
            "schema_version": (
                "camp_dp_v25_fair_pool_adaptation_contract_"
                "independent_review_v1"
            ),
            "status": "passed_independent_literal_contract_review",
            "source": {"path": str(source), "root_sha256": source_root},
            "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "literal_review": literal,
            "reviewer_imported_producer_contract_module": False,
            "reviewer_local_manifest_oracle": True,
            "reviewer_local_threshold_and_decision_oracle": True,
            "acquisition_authorized": False,
            "all_run_counts_zero": True,
            "fresh_or_b4_outcome_read": False,
            "claim_authorized": False,
            "review_head": _git_head(ROOT),
            "fixed_dp_head": EXPECTED_FIXED_DP,
        }
        (staging / "report.json").write_bytes(_canonical(report))
        (staging / "HEADS.json").write_bytes(
            _canonical(
                {
                    "review_head": report["review_head"],
                    "fixed_dp_head": EXPECTED_FIXED_DP,
                }
            )
        )
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(
            staging, label="V25 fair-pool adaptation contract review"
        )
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 fair-pool adaptation contract review"
        )
        return root
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()


def _tracked(repo: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=no"],
            cwd=repo,
            text=True,
        ).strip()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    args = parser.parse_args()
    print(review(**vars(args)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

