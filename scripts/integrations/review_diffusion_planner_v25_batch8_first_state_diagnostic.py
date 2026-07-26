"""Seal an independent raw-byte/source review of the one-call batch8 diagnostic."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_batch8_first_state_diagnostic_review import (  # noqa: E402
    independent_receipt_review,
)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain object")
    return value


def _source_topology(path: Path) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "model"
    ]
    if len(calls) != 1:
        raise ValueError("diagnostic must contain exactly one formal model call")
    cursor: ast.AST | None = calls[0]
    while cursor in parents:
        cursor = parents[cursor]
        if isinstance(cursor, (ast.For, ast.AsyncFor, ast.While)):
            raise ValueError("formal model call must not be inside a loop")
    forbidden = (
        "score_candidate_pool",
        "select_candidate",
        "Static14D",
        "Scene14D",
    )
    if any(token in source for token in forbidden):
        raise ValueError("selector path appears in preselector diagnostic")
    return {
        "formal_model_call_ast_count": 1,
        "formal_model_call_inside_loop": False,
        "selector_path_present": False,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def review(
    *,
    source: Path,
    source_root: str,
    contract_dir: Path,
    contract_root: str,
    output: Path,
) -> str:
    verify_complete_seal(source, source_root, label="batch8 first-state diagnostic")
    verify_complete_seal(contract_dir, contract_root, label="diagnostic contract")
    contract = _json(contract_dir / "contract.json")
    producer_path = (
        ROOT
        / "scripts"
        / "integrations"
        / "materialize_diffusion_planner_v25_batch8_first_state_diagnostic.py"
    )
    topology = _source_topology(producer_path)
    if (
        topology["source_sha256"]
        != contract["source_sha256"]["diagnostic_script"]
    ):
        raise RuntimeError("diagnostic producer source drifted")
    receipt = _json(source / "receipt.json")
    with np.load(source / "expanded_input_tensors.npz", allow_pickle=False) as archive:
        expanded = {
            name: np.ascontiguousarray(np.array(archive[name], copy=True))
            for name in archive.files
        }
    latent = np.fromfile(source / "latent_tensor.f32le", dtype="<f4").reshape(
        8, 321, 81, 4
    )
    candidate = np.fromfile(
        source / "candidate_tensor.f32le", dtype="<f4"
    ).reshape(8, 80, 4)
    neighbor = np.fromfile(
        source / "neighbor_tensor.f32le", dtype="<f4"
    ).reshape(8, 32, 80, 4)
    rebuilt = independent_receipt_review(
        receipt=receipt,
        latent=latent,
        expanded_inputs=expanded,
        candidate=candidate,
        neighbor=neighbor,
    )
    producer_report = _json(source / "report.json")
    if (
        producer_report.get("status")
        != "diagnostic_completed_stop_before_selector"
        or producer_report.get("taxonomy") != rebuilt["taxonomy"]
        or producer_report.get("formal_model_invocation_count") != 1
        or producer_report.get("sequential_model_call_count") != 0
        or producer_report.get("selector_call_count") != 0
        or producer_report.get("outcome_read") is not False
        or producer_report.get("old_artifact_cas_write_count") != 0
    ):
        raise RuntimeError("diagnostic producer report drifted")
    report = {
        **rebuilt,
        **topology,
        "schema_version": (
            "camp_dp_v25_single_invocation_batch8_first_state_diagnostic_"
            "independent_review_artifact_v1"
        ),
        "status": "passed_independent_raw_byte_and_source_review",
        "source_root_sha256": source_root,
        "contract_root_sha256": contract_root,
        "outcome_read": False,
        "old_artifact_cas_write_count": 0,
    }
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(
            (
                json.dumps(
                    report,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
                + "\n"
            ).encode("ascii")
        )
        (staging / "COMMAND").write_text(" ".join(sys.argv) + "\n", "utf-8")
        (staging / "run.exit").write_text("0\n", "ascii")
        root = seal_artifact(
            staging, label="V25 batch8 first-state diagnostic review"
        )
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 batch8 first-state diagnostic review"
        )
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        review(
            source=args.source,
            source_root=args.source_root,
            contract_dir=args.contract,
            contract_root=args.contract_root,
            output=args.output,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
