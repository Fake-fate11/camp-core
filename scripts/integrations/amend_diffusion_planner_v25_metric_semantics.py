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
from camp_core.integrations.diffusion_planner_v25_actual_native_receipt_contract import (  # noqa: E402
    validate_actual_native_receipt,
)
from camp_core.integrations.diffusion_planner_v25_metric_semantics import (  # noqa: E402
    build_amendment,
    summarize_run,
    validate_amendment_shape,
)


SCHEMA_VERSION = "camp_dp_v25_metric_semantics_amendment_artifact_v1"


def amend(
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
    contract: Path,
    contract_root: str,
    contract_review: Path,
    contract_review_root: str,
    continuation_ledger: Path,
    continuation_ledger_sha256: str,
) -> str:
    for label, path, root in (
        ("execution", execution, execution_root),
        ("execution review", execution_review, execution_review_root),
        ("corrected evaluation", evaluation, evaluation_root),
        ("corrected evaluation review", evaluation_review, evaluation_review_root),
        ("metric contract", contract, contract_root),
        ("metric contract review", contract_review, contract_review_root),
    ):
        verify_complete_seal(path, root, label=f"Fresh B4 {label}")
    if _file_sha256(continuation_ledger) != continuation_ledger_sha256:
        raise ValueError("continuation ledger SHA drifted")
    contract_report = _object(contract / "report.json")
    contract_review_report = _object(contract_review / "report.json")
    if (
        contract_report.get("outcome_values_read") is not False
        or contract_review_report.get("status")
        != "passed_independent_outcome_free_contract_review"
        or contract_review_report.get("outcome_values_read") is not False
    ):
        raise ValueError("metric amendment contract/review is not eligible")

    rows = _list(execution / "evaluation_rows.json")
    terminals = _list(execution / "run_terminals.json")
    run_dirs = sorted((execution / "runs").iterdir())
    if (
        len(rows) != 1500
        or len(terminals) != 1500
        or len(run_dirs) != 1500
        or any(not path.is_dir() for path in run_dirs)
    ):
        raise ValueError("sealed Fresh B4 denominator drifted")
    row_by_key = {
        (row.get("pair_key"), row.get("arm")): row for row in rows
    }
    if len(row_by_key) != 1500:
        raise ValueError("sealed evaluation-row identity drifted")
    summaries: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for run_dir, terminal in zip(run_dirs, terminals, strict=True):
        stored_terminal = _object(run_dir / "terminal.json")
        if stored_terminal != terminal or terminal.get("status") != "complete":
            raise ValueError("sealed complete run terminal drifted")
        pair_key = terminal.get("unit_sha256")
        arm = terminal.get("evaluation_arm")
        key = (pair_key, arm)
        if key in seen or key not in row_by_key:
            raise ValueError("sealed run/evaluation-row binding drifted")
        seen.add(key)
        native = _object(run_dir / "native_receipt.json")
        if _canonical_sha(native) != terminal.get("native_receipt_sha256"):
            raise ValueError("sealed native receipt SHA drifted")
        raw_path = run_dir / "actual_native_receipt_raw.json"
        if raw_path.is_file():
            raw = _object(raw_path)
            validate_actual_native_receipt(
                raw,
                branch=(
                    "candidate0_primary"
                    if arm == "candidate0"
                    else "static14d" if arm == "static14d" else "scene14d"
                ),
            )
            projected = dict(native)
            projected.pop("fresh_decision_evidence_reference", None)
            projected.pop("fresh_decision_evidence_count", None)
            if raw != projected:
                raise ValueError("sealed raw/projected native receipt drifted")
        summaries.append(summarize_run(native, row_by_key[key]))
    if len(seen) != 1500:
        raise ValueError("sealed Fresh B4 run inventory incomplete")
    bindings = {
        "execution": _binding(execution, execution_root),
        "execution_review": _binding(execution_review, execution_review_root),
        "corrected_evaluation": _binding(evaluation, evaluation_root),
        "corrected_evaluation_review": _binding(
            evaluation_review, evaluation_review_root
        ),
        "contract": _binding(contract, contract_root),
        "contract_review": _binding(contract_review, contract_review_root),
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
        "amendment_implementation_head": _git_head(),
    }
    amendment = build_amendment(
        summaries,
        bindings=bindings,
        contract_root_sha256=contract_root,
        contract_review_root_sha256=contract_review_root,
        source_file_sha256=_file_sha256(execution / "evaluation_rows.json"),
    )
    validate_amendment_shape(amendment)
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "sealed_metric_semantics_amendment",
        "amendment": amendment,
        "execution_read_only": True,
        "execution_files_written": False,
        "evaluation_rerun": False,
        "fresh_execution_rerun": False,
        "dp_or_k8_run": False,
        "scientific_or_continuation_cas_written": False,
        "claim_changed": False,
        "implementation_head": _git_head(),
    }
    return _write_atomic(output, report)


def _write_atomic(output: Path, report: dict[str, Any]) -> str:
    output = output.resolve()
    if output.exists():
        raise ValueError("metric-semantics amendment output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(_canonical_bytes(report))
        (staging / "HEADS.json").write_bytes(
            _canonical_bytes(
                {
                    "role": "metric_semantics_amendment",
                    "implementation_head": report["implementation_head"],
                    "execution_source_head": report["amendment"]["bindings"][
                        "execution_source_head"
                    ],
                    "execution_pointer_head": report["amendment"]["bindings"][
                        "execution_pointer_head"
                    ],
                    "fixed_dp_head": report["amendment"]["bindings"]["fixed_dp_head"],
                }
            )
        )
        root = seal_artifact(staging, label="V25 metric-semantics amendment")
        os.replace(staging, output)
        verify_complete_seal(output, root, label="V25 metric-semantics amendment")
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _binding(path: Path, root: str) -> dict[str, str]:
    return {"path": str(path.resolve()), "root_sha256": root}


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain an object")
    return value


def _list(path: Path) -> list[Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not list:
        raise ValueError(f"{path} must contain a list")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    for name in (
        "output",
        "execution",
        "execution_review",
        "evaluation",
        "evaluation_review",
        "contract",
        "contract_review",
        "continuation_ledger",
    ):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    for name in (
        "execution_root",
        "execution_review_root",
        "evaluation_root",
        "evaluation_review_root",
        "contract_root",
        "contract_review_root",
        "continuation_ledger_sha256",
    ):
        parser.add_argument(f"--{name.replace('_', '-')}", required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    print(amend(**vars(args)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
