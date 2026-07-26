"""Independent raw-byte review and pair reconstruction for generator calibration."""

from __future__ import annotations

import argparse
from itertools import combinations
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "camp_core"
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))

from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact, verify_complete_seal  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_batch8_generator_calibration import EXACT_DIRS  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_batch8_generator_calibration_review import (  # noqa: E402
    CANDIDATE_SHAPE, F32, NEIGHBOR_SHAPE, endpoint_registry, pair_errors,
    sha256_bytes, state_q99,
)


def review(raw_dir: Path, raw_root: str, preflight_dir: Path, preflight_root: str, output: Path) -> str:
    verify_complete_seal(raw_dir, raw_root, label="generator calibration raw")
    verify_complete_seal(preflight_dir, preflight_root, label="generator calibration preflight")
    raw = json.loads((raw_dir / "report.json").read_text("ascii"))
    if raw["completed_run_count"] != 320 or raw["formal_model_call_count"] != 320:
        raise RuntimeError("raw denominator drifted")
    all_runs = {}
    failures = []
    for slot in range(320):
        receipt = json.loads((raw_dir / "runs" / f"{slot:03d}" / "receipt.json").read_text("ascii"))
        if (
            receipt["slot"] != slot
            or receipt["formal_model_call_count"] != 1
            or receipt["sequential_model_call_count"] != 0
            or receipt["selector_call_count"] != 0
            or receipt["post_pool_model_dp_latent_candidate_generation_call_count"] != 0
            or receipt["expanded_batch_size"] != 8
            or receipt["source_ego_state_count"] != 1
            or receipt["agent_as_ego_batch"] is not False
        ):
            raise RuntimeError("run binding drifted")
        cpath = raw_dir / receipt["candidate_relpath"]
        npath = raw_dir / receipt["neighbor_relpath"]
        cbytes, nbytes = cpath.read_bytes(), npath.read_bytes()
        if sha256_bytes(cbytes) != receipt["candidate"]["tensor_sha256"] or sha256_bytes(nbytes) != receipt["neighbor"]["tensor_sha256"]:
            raise RuntimeError("tensor SHA drifted")
        candidate = np.frombuffer(cbytes, dtype=F32).reshape(CANDIDATE_SHAPE).copy()
        neighbor = np.frombuffer(nbytes, dtype=F32).reshape(NEIGHBOR_SHAPE).copy()
        crows = [sha256_bytes(np.ascontiguousarray(row).tobytes(order="C")) for row in candidate]
        nrows = [sha256_bytes(np.ascontiguousarray(row).tobytes(order="C")) for row in neighbor]
        if crows != receipt["candidate"]["row_sha256"] or nrows != receipt["neighbor"]["row_sha256"]:
            raise RuntimeError("row SHA drifted")
        actual_reasons = []
        if not np.isfinite(candidate).all():
            actual_reasons.append("candidate_nonfinite")
        if len(set(crows)) != 8:
            actual_reasons.append("candidate_nondiverse")
        if not np.isfinite(neighbor).all():
            actual_reasons.append("neighbor_nonfinite")
        if actual_reasons != receipt["failure_reasons"]:
            raise RuntimeError("typed failure taxonomy drifted")
        if actual_reasons:
            failures.append({"slot": slot, "reasons": actual_reasons})
        all_runs[(receipt["state_index"], receipt["repeat_index"])] = (candidate, neighbor)
    pair_rows = []
    state_values = {row["endpoint_id"]: [] for row in endpoint_registry()}
    if not failures:
        for state in range(64):
            per_endpoint = {key: [] for key in state_values}
            for left, right in combinations(range(5), 2):
                values = pair_errors(*all_runs[(state, left)], *all_runs[(state, right)])
                pair_rows.append({"state_index": state, "repeat_left": left, "repeat_right": right, "values": values})
                for key, value in values.items():
                    per_endpoint[key].append(value)
            for key, values in per_endpoint.items():
                state_values[key].append(state_q99(values))
    report = {
        "schema_version": "camp_dp_v25_batch8_generator_calibration_raw_independent_review_v1",
        "status": "PASS" if not failures else "FAIL_TYPED_OUTPUTS_FULL_DENOMINATOR",
        "reviewed_raw_root_sha256": raw_root,
        "reviewed_preflight_root_sha256": preflight_root,
        "raw_receipt_count": 320,
        "formal_model_call_count": 320,
        "pair_receipt_count": len(pair_rows),
        "state_count": 64,
        "typed_failure_count": len(failures),
        "typed_failures": failures,
        "hard_integrity_failure_count": 0,
        "pair_receipts": pair_rows,
        "state_q99_values": state_values,
        "producer_generator_endpoint_threshold_oracle_imported": False,
        "selector_call_count": 0,
        "outcome_read": False,
    }
    return _atomic(output, report)


def _atomic(output: Path, report: dict) -> str:
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent))
    try:
        (staging / "report.json").write_text(json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n", encoding="ascii")
        root = seal_artifact(staging, label="V25 batch8 generator calibration raw independent review")
        os.replace(staging, output)
        verify_complete_seal(output, root, label="V25 batch8 generator calibration raw independent review")
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--raw-dir", type=Path, default=Path(EXACT_DIRS["raw"]))
    p.add_argument("--raw-root", required=True)
    p.add_argument("--preflight-dir", type=Path, default=Path(EXACT_DIRS["preflight"]))
    p.add_argument("--preflight-root", required=True)
    p.add_argument("--output", type=Path, default=Path(EXACT_DIRS["raw_review"]))
    a = p.parse_args()
    print(review(a.raw_dir, a.raw_root, a.preflight_dir, a.preflight_root, a.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
