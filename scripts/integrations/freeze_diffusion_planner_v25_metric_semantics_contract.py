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
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_metric_semantics import (  # noqa: E402
    metric_semantics_contract,
    validate_metric_semantics_contract,
)


SCHEMA_VERSION = "camp_dp_v25_metric_semantics_amendment_contract_artifact_v1"
STATUS = "sealed_outcome_independent_metric_semantics_contract"
IMPLEMENTATION_PATHS = (
    "camp_core/camp_core/integrations/diffusion_planner_v25_metric_semantics.py",
    "scripts/integrations/freeze_diffusion_planner_v25_metric_semantics_contract.py",
    "scripts/integrations/review_diffusion_planner_v25_metric_semantics_contract.py",
    "scripts/integrations/amend_diffusion_planner_v25_metric_semantics.py",
    "scripts/integrations/review_diffusion_planner_v25_metric_semantics_amendment.py",
)


def freeze(
    *,
    output: Path,
    execution: Path,
    execution_root: str,
    execution_review: Path,
    execution_review_root: str,
    evaluation: Path,
    evaluation_root: str,
    evaluation_review: Path,
    evaluation_review_root: str,
    continuation_ledger: Path,
    continuation_ledger_sha256: str,
) -> str:
    for label, path, root in (
        ("execution", execution, execution_root),
        ("execution review", execution_review, execution_review_root),
        ("corrected evaluation", evaluation, evaluation_root),
        ("corrected evaluation review", evaluation_review, evaluation_review_root),
    ):
        verify_complete_seal(path, root, label=f"Fresh B4 {label}")
    if _file_sha256(continuation_ledger) != continuation_ledger_sha256:
        raise ValueError("continuation ledger SHA drifted")
    contract = validate_metric_semantics_contract(metric_semantics_contract())
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "outcome_values_read": False,
        "sealed_execution_written": False,
        "scientific_or_continuation_cas_written": False,
        "bindings": {
            "execution": _binding(execution, execution_root),
            "execution_review": _binding(execution_review, execution_review_root),
            "corrected_evaluation": _binding(evaluation, evaluation_root),
            "corrected_evaluation_review": _binding(
                evaluation_review, evaluation_review_root
            ),
            "continuation_ledger": {
                "path": str(continuation_ledger.resolve()),
                "sha256": continuation_ledger_sha256,
                "state": "independently_reviewed_terminal",
            },
            "holdout_identity_sha256": (
                "5f2f8e2c2eb90927ec485a8d0baa3935b155e82d90b04fa3d456fc845cd8464a"
            ),
            "experiment_protocol_sha256": (
                "aa79576f8ac487e2ce197c481d57f9c5d350a41d9522096975786207ef76785f"
            ),
            "execution_plan_sha256": (
                "41442dd7d71552972d737d9a9e3d56e9827f864e0c06e11c57487f651206dee0"
            ),
            "nonce": (
                "8680c1b19ce0620b7dc2ec9453ffde0da024d3443e6d6307fc41e87f3dad3b42"
            ),
            "fixed_dp_head": "7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "execution_source_head": "7be93df20deee03587b9898e8560909662df972c",
            "execution_pointer_head": "06d3a1f3a37061f93f5c9788312ae59d1356d126",
        },
        "implementation": _implementation_manifest(),
        "contract": contract,
    }
    return _write_atomic(output, report)


def _implementation_manifest() -> dict[str, Any]:
    head = _git_head()
    rows = [
        {"path": relative, "sha256": _file_sha256(ROOT / relative)}
        for relative in IMPLEMENTATION_PATHS
    ]
    return {
        "git_head": head,
        "tracked_clean": not _tracked_changes(),
        "paths": rows,
        "manifest_sha256": hashlib.sha256(_canonical_bytes(rows)).hexdigest(),
    }


def _write_atomic(output: Path, report: dict[str, Any]) -> str:
    output = output.resolve()
    if output.exists():
        raise ValueError("metric-semantics contract output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        _write_json(staging / "report.json", report)
        _write_json(
            staging / "HEADS.json",
            {
                "role": "metric_semantics_contract",
                "implementation_head": report["implementation"]["git_head"],
                "execution_source_head": report["bindings"]["execution_source_head"],
                "execution_pointer_head": report["bindings"]["execution_pointer_head"],
                "fixed_dp_head": report["bindings"]["fixed_dp_head"],
            },
        )
        root = seal_artifact(staging, label="V25 metric-semantics contract")
        os.replace(staging, output)
        verify_complete_seal(output, root, label="V25 metric-semantics contract")
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _binding(path: Path, root: str) -> dict[str, str]:
    return {"path": str(path.resolve()), "root_sha256": root}


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _tracked_changes() -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=no"],
            cwd=ROOT,
            text=True,
        ).strip()
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    for name in (
        "output",
        "execution",
        "execution_review",
        "evaluation",
        "evaluation_review",
        "continuation_ledger",
    ):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    for name in (
        "execution_root",
        "execution_review_root",
        "evaluation_root",
        "evaluation_review_root",
        "continuation_ledger_sha256",
    ):
        parser.add_argument(f"--{name.replace('_', '-')}", required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    root = freeze(**vars(args))
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
