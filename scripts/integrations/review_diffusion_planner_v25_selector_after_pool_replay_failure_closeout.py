"""Independent literal review of the immutable replay wiring failure closeout."""

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
FAILED_REPLAY = AUTODL / "camp_dp_v25_selector_after_pool_replay_v3_59874f4a"
FAILED_REPLAY_ROOT = (
    "7a85ef00c10a79aa1b8e92729f51d9512e5e67d53d1ef44e00da55d19840109d"
)
PREFLIGHT = AUTODL / "camp_dp_v25_selector_after_pool_replay_preflight_v3_59874f4a"
PREFLIGHT_ROOT = (
    "6b7bfc0edfa87e75a64dd82775d4ad8d427a11bdebe5fd24ba995b3ef7a45539"
)
CLOSEOUT = AUTODL / (
    "camp_dp_v25_selector_after_pool_replay_failure_closeout_v1_"
    "4c412870_e6579ca7"
)
OUTPUT = AUTODL / (
    "camp_dp_v25_selector_after_pool_replay_failure_closeout_review_v1_"
    "4c412870_e6579ca7"
)
MATERIALIZER_PATH = (
    "scripts/integrations/materialize_diffusion_planner_v25_selector_after_pool_replay.py"
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


def review(*, repo: Path, closeout_root: str, output: Path = OUTPUT) -> str:
    if (
        sys.executable != "/root/autodl-tmp/dp312_venv/bin/python"
        or sys.version_info[:3] != (3, 12, 3)
        or sys.prefix != "/root/autodl-tmp/dp312_venv"
    ):
        raise RuntimeError("failure reviewer Python authority drifted")
    if output != OUTPUT or output.exists():
        raise RuntimeError("failure review exact output drifted or exists")
    for path, root, label in (
        (FAILED_REPLAY, FAILED_REPLAY_ROOT, "failed selector replay"),
        (PREFLIGHT, PREFLIGHT_ROOT, "selector replay preflight"),
        (CLOSEOUT, closeout_root, "selector replay failure closeout"),
    ):
        verify_complete_seal(path, root, label=label)
    failed_report = _json(FAILED_REPLAY / "report.json")
    closeout = _json(CLOSEOUT / "report.json")
    receipts = [
        json.loads(line)
        for line in (FAILED_REPLAY / "receipts.jsonl")
        .read_text(encoding="ascii")
        .splitlines()
        if line
    ]
    if len(receipts) != 320:
        raise ValueError("independent failure denominator drifted")
    state_repeat = set()
    line_hashes = []
    for slot, receipt in enumerate(receipts):
        if (
            receipt.get("slot") != slot
            or receipt.get("status") != "typed_failure_retained"
            or receipt.get("selector_call_count") != 1
            or receipt.get("failure", {}).get("exception_type") != "ValueError"
            or receipt.get("failure", {}).get("message")
            != "weights must be a nonnegative simplex [14]"
            or receipt.get("candidate_tensor_sha256_before")
            != receipt.get("candidate_tensor_sha256_after")
            or receipt.get("neighbor_tensor_sha256_before")
            != receipt.get("neighbor_tensor_sha256_after")
        ):
            raise ValueError(f"independent failure receipt drifted: {slot}")
        state_repeat.add((receipt.get("state_index"), receipt.get("repeat_index")))
        line_hashes.append(_sha(_canonical(receipt)))
    if state_repeat != {(state, repeat) for state in range(64) for repeat in range(5)}:
        raise ValueError("independent failure state/repeat inventory drifted")
    with np.load(PREFLIGHT / "selector_assets.npz", allow_pickle=False) as archive:
        weights = np.ascontiguousarray(
            np.asarray(archive["static14d_weights"], dtype=np.float64)
        )
    independent_weights = {
        "shape": list(weights.shape),
        "dtype": weights.dtype.str,
        "finite": bool(np.isfinite(weights).all()),
        "sum": float(np.sum(weights)),
        "minimum": float(np.min(weights)),
        "negative_count": int(np.count_nonzero(weights < 0.0)),
        "below_accepted_atol_count": int(np.count_nonzero(weights < -1e-9)),
        "accepted_simplex_nonnegative_atol": 1e-9,
        "weights_sha256": _sha(weights.tobytes(order="C")),
    }
    source = _git_blob(repo, BASE_HEAD, MATERIALIZER_PATH)
    text = source.decode("utf-8")
    call_start = next(
        index
        for index, line in enumerate(text.splitlines(), start=1)
        if "static_prod = select_camp_candidate(" in line
    )
    if "simplex_nonnegative_atol" in "\n".join(
        text.splitlines()[call_start - 1 : call_start + 8]
    ):
        raise ValueError("pinned failed Static call unexpectedly carried tolerance")
    expected = {
        "schema_version": (
            "camp_dp_v25_selector_after_pool_replay_failure_closeout_v1"
        ),
        "status": "PASS_engineering_failure_closeout",
        "authority_sha256": AUTHORITY_SHA256,
        "base_head": BASE_HEAD,
        "failed_replay_root_sha256": FAILED_REPLAY_ROOT,
        "failed_replay_classification": (
            "full_denominator_preselector_tolerance_wiring_failure"
        ),
        "completed_slot_count": 320,
        "typed_failure_count": 320,
        "static_selector_call_count": 320,
        "scene_selector_call_count": 0,
        "model_call_count": 0,
        "dp_call_count": 0,
        "latent_generation_call_count": 0,
        "candidate_generation_call_count": 0,
        "tensor_mutation_count": 0,
        "weights": independent_weights,
    }
    for key, value in expected.items():
        if closeout.get(key) != value:
            raise ValueError(f"independent closeout semantic drift: {key}")
    if (
        failed_report.get("typed_failure_count") != 320
        or failed_report.get("selector_call_count") != 320
        or failed_report.get("tensor_mutation_count") != 0
        or closeout.get("pinned_call_site", {}).get("base_blob_sha256") != _sha(source)
        or closeout.get("pinned_call_site", {}).get("line") != call_start
        or closeout.get("receipt_line_sha256") != line_hashes
        or closeout.get("replacement_replay_authorized") is not True
        or closeout.get("fresh_or_holdout_outcome_read") is not False
        or closeout.get("old_artifact_or_cas_write") is not False
        or closeout.get("claim_authorized") is not False
    ):
        raise ValueError("independent failure closeout boundary drifted")
    report = {
        "schema_version": (
            "camp_dp_v25_selector_after_pool_replay_failure_closeout_review_v1"
        ),
        "status": "PASS_independent_engineering_failure_review",
        "reviewed_closeout_root_sha256": closeout_root,
        "reviewed_failed_replay_root_sha256": FAILED_REPLAY_ROOT,
        "reviewed_slot_count": 320,
        "reviewed_state_count": 64,
        "reviewed_repeat_count_per_state": 5,
        "static_selector_call_count": 320,
        "scene_selector_call_count": 0,
        "model_dp_latent_generation_call_count": 0,
        "tensor_mutation_count": 0,
        "weight_bytes_independently_rebuilt": True,
        "pinned_source_blob_independently_rebuilt": True,
        "producer_failure_or_decision_oracle_imported": False,
        "classification": (
            "full_denominator_preselector_tolerance_wiring_failure"
        ),
        "weights_drift_claimed": False,
        "scientific_failure_claimed": False,
        "training_support_ood_or_retraining_claimed": False,
        "project_terminal_claimed": False,
        "fresh_or_holdout_outcome_read": False,
        "old_artifact_or_cas_write": False,
        "claim_authorized": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent)
    )
    try:
        (staging / "report.json").write_bytes(_canonical(report))
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(
            staging, label="V25 selector replay failure closeout review"
        )
        os.replace(staging, output)
        verify_complete_seal(
            output,
            root,
            label="V25 selector replay failure closeout review",
        )
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--closeout-root", required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(review(repo=args.repo, closeout_root=args.closeout_root, output=args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
