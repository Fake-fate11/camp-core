"""Seal the immutable selector replay tolerance-wiring failure.

This is an outcome-free engineering closeout.  It reads only the already
sealed selector replay, its preflight assets, and the pinned source blob.
"""

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

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "camp_core"
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)


AUTODL = Path("/root/autodl-tmp")
BASE_HEAD = "4c412870118962ee49917bcc2090be18836fe709"
AUTHORITY_SHA256 = (
    "e6579ca71ccfdd7e0a94d52450b2473d4b8c52c38e8b0504e0dcb8b35935ab3c"
)
PARENT_AUTHORITY_SHA256 = (
    "9caf4b809b5cba3a21659bea007152e4ed42e78a9f61965b4becdbafa7ee77ad"
)
FAILED_REPLAY = AUTODL / "camp_dp_v25_selector_after_pool_replay_v3_59874f4a"
FAILED_REPLAY_ROOT = (
    "7a85ef00c10a79aa1b8e92729f51d9512e5e67d53d1ef44e00da55d19840109d"
)
PREFLIGHT = AUTODL / "camp_dp_v25_selector_after_pool_replay_preflight_v3_59874f4a"
PREFLIGHT_ROOT = (
    "6b7bfc0edfa87e75a64dd82775d4ad8d427a11bdebe5fd24ba995b3ef7a45539"
)
OUTPUT = AUTODL / (
    "camp_dp_v25_selector_after_pool_replay_failure_closeout_v1_"
    "4c412870_e6579ca7"
)
MATERIALIZER_PATH = (
    "scripts/integrations/materialize_diffusion_planner_v25_selector_after_pool_replay.py"
)
EXPECTED_MESSAGE = "weights must be a nonnegative simplex [14]"
EXPECTED_STATIC_CALL = (
    "select_camp_candidate(candidates=candidate,materialized=materialized,"
    "atom_scales=assets.atom_scales,weights=assets.static14d_weights,"
    'eligibility_mask_name="source_valid_mask")'
)


def _canonical(value: Any) -> bytes:
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


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain an object")
    return value


def _git_blob(repo: Path, revision: str, relative: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{revision}:{relative}"]
    )


def _normalized_call(source: bytes) -> tuple[int, str]:
    text = source.decode("utf-8")
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if "static_prod = select_camp_candidate(" not in line:
            continue
        collected = [line.split("static_prod = ", 1)[1].strip()]
        for cursor in range(index + 1, len(lines)):
            collected.append(lines[cursor].strip())
            if lines[cursor].strip() == ")":
                break
        normalized = "".join(collected)
        if normalized == EXPECTED_STATIC_CALL:
            return index + 1, normalized
    raise ValueError("pinned Static selector call site not found")


def closeout(*, repo: Path, output: Path = OUTPUT) -> str:
    if (
        sys.executable != "/root/autodl-tmp/dp312_venv/bin/python"
        or sys.version_info[:3] != (3, 12, 3)
        or sys.prefix != "/root/autodl-tmp/dp312_venv"
    ):
        raise RuntimeError("failure closeout Python authority drifted")
    if output != OUTPUT or output.exists():
        raise RuntimeError("failure closeout exact output drifted or exists")
    verify_complete_seal(
        FAILED_REPLAY, FAILED_REPLAY_ROOT, label="failed selector replay"
    )
    verify_complete_seal(PREFLIGHT, PREFLIGHT_ROOT, label="selector replay preflight")
    report = _json(FAILED_REPLAY / "report.json")
    receipts = [
        json.loads(line)
        for line in (FAILED_REPLAY / "receipts.jsonl")
        .read_text(encoding="ascii")
        .splitlines()
        if line
    ]
    expected_receipt_keys = {
        "schema_version",
        "slot",
        "run_id",
        "state_index",
        "repeat_index",
        "forward_id",
        "pool_id",
        "candidate_tensor_sha256",
        "neighbor_tensor_sha256",
        "candidate_row_sha256",
        "candidate_relpath",
        "neighbor_relpath",
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "neighbor_tensor_sha256_before",
        "neighbor_tensor_sha256_after",
        "formal_model_call_count",
        "dp_call_count",
        "latent_generation_call_count",
        "candidate_generation_call_count",
        "selector_call_count",
        "status",
        "failure",
        "receipt_sha256",
    }
    if (
        len(receipts) != 320
        or report.get("completed_slot_count") != 320
        or report.get("typed_failure_count") != 320
        or report.get("selector_call_count") != 320
        or report.get("formal_model_call_count") != 0
        or report.get("dp_call_count") != 0
        or report.get("latent_generation_call_count") != 0
        or report.get("candidate_generation_call_count") != 0
        or report.get("tensor_mutation_count") != 0
    ):
        raise ValueError("failed replay denominator/call evidence drifted")
    for slot, receipt in enumerate(receipts):
        if (
            set(receipt) != expected_receipt_keys
            or receipt.get("slot") != slot
            or receipt.get("status") != "typed_failure_retained"
            or receipt.get("selector_call_count") != 1
            or receipt.get("formal_model_call_count") != 0
            or receipt.get("dp_call_count") != 0
            or receipt.get("latent_generation_call_count") != 0
            or receipt.get("candidate_generation_call_count") != 0
            or receipt.get("candidate_tensor_sha256_before")
            != receipt.get("candidate_tensor_sha256_after")
            or receipt.get("neighbor_tensor_sha256_before")
            != receipt.get("neighbor_tensor_sha256_after")
            or receipt.get("failure")
            != {
                "taxonomy": "selector_replay_typed_failure_retained",
                "exception_type": "ValueError",
                "message": EXPECTED_MESSAGE,
            }
        ):
            raise ValueError(f"failed replay receipt drifted: {slot}")
        supplied = receipt["receipt_sha256"]
        payload = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
        if supplied != _sha(_canonical(payload)):
            raise ValueError(f"failed replay receipt digest drifted: {slot}")
    with np.load(PREFLIGHT / "selector_assets.npz", allow_pickle=False) as archive:
        weights = np.ascontiguousarray(
            np.asarray(archive["static14d_weights"], dtype=np.float64)
        )
    if weights.shape != (14,) or not np.isfinite(weights).all():
        raise ValueError("failed replay Static weight evidence drifted")
    source = _git_blob(repo, BASE_HEAD, MATERIALIZER_PATH)
    source_line, normalized_call = _normalized_call(source)
    weight_evidence = {
        "shape": [14],
        "dtype": weights.dtype.str,
        "finite": True,
        "sum": float(weights.sum()),
        "minimum": float(weights.min()),
        "negative_count": int(np.count_nonzero(weights < 0.0)),
        "below_accepted_atol_count": int(np.count_nonzero(weights < -1e-9)),
        "accepted_simplex_nonnegative_atol": 1e-9,
        "weights_sha256": _sha(weights.tobytes(order="C")),
    }
    expected_weight_evidence = {
        "shape": [14],
        "dtype": "<f8",
        "finite": True,
        "sum": 1.0000000000000004,
        "minimum": -5.9639495628241106e-18,
        "negative_count": 1,
        "below_accepted_atol_count": 0,
        "accepted_simplex_nonnegative_atol": 1e-9,
        "weights_sha256": weight_evidence["weights_sha256"],
    }
    if weight_evidence != expected_weight_evidence:
        raise ValueError("failed replay weight evidence changed")
    receipt_inventory = [_sha(line.encode("ascii") + b"\n") for line in (
        FAILED_REPLAY / "receipts.jsonl"
    ).read_text(encoding="ascii").splitlines()]
    payload = {
        "schema_version": (
            "camp_dp_v25_selector_after_pool_replay_failure_closeout_v1"
        ),
        "status": "PASS_engineering_failure_closeout",
        "authority_sha256": AUTHORITY_SHA256,
        "parent_authority_sha256": PARENT_AUTHORITY_SHA256,
        "base_head": BASE_HEAD,
        "failed_replay_root_sha256": FAILED_REPLAY_ROOT,
        "failed_replay_classification": (
            "full_denominator_preselector_tolerance_wiring_failure"
        ),
        "planned_slot_count": 320,
        "completed_slot_count": 320,
        "typed_failure_count": 320,
        "static_selector_call_count": 320,
        "scene_selector_call_count": 0,
        "model_call_count": 0,
        "dp_call_count": 0,
        "latent_generation_call_count": 0,
        "candidate_generation_call_count": 0,
        "tensor_mutation_count": 0,
        "exception": {
            "type": "ValueError",
            "message": EXPECTED_MESSAGE,
            "first_arm": "Static14D",
            "second_arm_started": False,
        },
        "pinned_call_site": {
            "relative_path": MATERIALIZER_PATH,
            "base_blob_sha256": _sha(source),
            "line": source_line,
            "normalized_call": normalized_call,
            "explicit_simplex_nonnegative_atol": None,
            "selector_default_used": 0.0,
        },
        "weights": weight_evidence,
        "receipt_line_sha256": receipt_inventory,
        "interpretation": (
            "ordinary preselector consumer tolerance wiring failure; not weights "
            "drift, selector scientific failure, training-support/OOD evidence, "
            "retraining evidence, or project termination"
        ),
        "replacement_replay_authorized": True,
        "fresh_or_holdout_outcome_read": False,
        "old_artifact_or_cas_write": False,
        "claim_authorized": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent)
    )
    try:
        (staging / "report.json").write_bytes(_canonical(payload))
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(
            staging, label="V25 selector-after-pool replay failure closeout"
        )
        os.replace(staging, output)
        verify_complete_seal(
            output,
            root,
            label="V25 selector-after-pool replay failure closeout",
        )
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(closeout(repo=args.repo, output=args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
