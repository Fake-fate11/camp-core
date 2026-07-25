"""Independent literal review of the V25 target-architecture amendment."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_target_architecture_review import (  # noqa: E402
    independently_review_amendment,
)


def review(*, source: Path, source_root: str, output: Path) -> str:
    verify_complete_seal(source, source_root, label="target architecture amendment")
    source_report = _object(source / "report.json")
    if (
        source_report.get("schema_version")
        != "camp_dp_v25_target_architecture_amendment_artifact_v1"
        or source_report.get("status")
        != "sealed_outcome_independent_target_architecture_amendment"
        or source_report.get("outcome_values_read") is not False
        or source_report.get("fresh_or_closed_loop_executed") is not False
        or source_report.get("training_executed") is not False
        or source_report.get("sealed_artifacts_or_cas_written") is not False
    ):
        raise ValueError("target architecture amendment producer invariant drifted")
    independently_review_amendment(source_report.get("amendment"))
    if (
        source_report.get("fixed_dp", {}).get("head")
        != "7a1d33da277a1992ec474b5383a0c963c72e04e4"
        or source_report.get("fixed_dp", {}).get("tracked_clean") is not True
    ):
        raise ValueError("fixed DP binding drifted")
    report = {
        "schema_version": (
            "camp_dp_v25_target_architecture_amendment_independent_review_v1"
        ),
        "status": "passed_independent_target_architecture_amendment_review",
        "source": {
            "path": str(source.resolve()),
            "root_sha256": source_root,
        },
        "reviewer_role": "separate_literal_architecture_contract_oracle",
        "producer_validator_imported": False,
        "existing_b4_reclassified_without_mutation": True,
        "target_same_ego_single_invocation_contract_verified": True,
        "selector_zero_model_call_contract_verified": True,
        "layered_fairness_draft_verified_not_executed": True,
        "outcome_values_read": False,
        "fresh_or_closed_loop_executed": False,
        "training_executed": False,
        "sealed_artifacts_or_cas_written": False,
        "review_head": _git_head(),
    }
    return _write_atomic(output, report)


def _write_atomic(output: Path, report: dict[str, Any]) -> str:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(_canonical_bytes(report))
        (staging / "HEADS.json").write_bytes(
            _canonical_bytes(
                {
                    "role": "target_architecture_amendment_review",
                    "review_head": report["review_head"],
                }
            )
        )
        root = seal_artifact(
            staging, label="V25 target architecture amendment review"
        )
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 target architecture amendment review"
        )
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain an object")
    return value


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


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        review(
            source=args.source,
            source_root=args.source_root,
            output=args.output,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
