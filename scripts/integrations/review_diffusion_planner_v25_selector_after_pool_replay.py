"""Independent raw-byte review of the zero-model selector-after-pool replay."""

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
from camp_core.integrations.diffusion_planner_v25_selector_after_pool_replay_review import (  # noqa: E402
    RAW_FEATURE_NAMES,
    literal_atoms,
    literal_context,
    literal_scene_weights,
    literal_selection,
    validate_slot_authority,
    verify_same_state,
)


AUTODL = Path("/root/autodl-tmp")
DP = AUTODL / "Diffusion-Planner"
CONTRACT = AUTODL / (
    "camp_dp_v25_selector_after_pool_replay_contract_v3_59874f4a"
)
CONTRACT_REVIEW = AUTODL / (
    "camp_dp_v25_selector_after_pool_replay_contract_review_v3_59874f4a"
)
PREFLIGHT = AUTODL / (
    "camp_dp_v25_selector_after_pool_replay_preflight_v3_59874f4a"
)
PREFLIGHT_REVIEW = AUTODL / (
    "camp_dp_v25_selector_after_pool_replay_preflight_review_v3_59874f4a"
)
REPLAY = AUTODL / "camp_dp_v25_selector_after_pool_replay_v3_59874f4a"
OUTPUT = AUTODL / (
    "camp_dp_v25_selector_after_pool_replay_review_v3_59874f4a"
)
CORRECTED_RAW = AUTODL / (
    "camp_dp_v25_batch8_generator_repeatability_corrected_raw_v1_dc76fbc8"
)
CORRECTED_RAW_REVIEW = AUTODL / (
    "camp_dp_v25_batch8_generator_repeatability_corrected_raw_review_v1_dc76fbc8"
)
TRAINING = AUTODL / "camp_dp_v25_camp_training_863e28da_20260722T103219CST"
TRAINING_REVIEW = AUTODL / (
    "camp_dp_v25_camp_training_review_8fecda47_20260722T122701CST"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
ROOTS = {
    "corrected_raw": (
        "731a715a0422f92e115bc078900d84c47b9f51f47c64181c3b8e71569cffdda4"
    ),
    "corrected_raw_review": (
        "c0e24bb60a4eb9694bfda099d4d6d9b9be07f85fb486577275f0b32178cfbfc8"
    ),
    "training": (
        "8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9"
    ),
    "training_review": (
        "ef2e9748a9ba0fff5b35f010cba6efd1b16d8e1dc0d562f5a7960c8dcb3d9be9"
    ),
}


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


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _array_sha(value: np.ndarray) -> str:
    return _sha(np.ascontiguousarray(value).tobytes(order="C"))


def _context_scaler_sha(q05: np.ndarray, q95: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(b"camp_dp_v25_context_scaler_v1\0")
    for name in RAW_FEATURE_NAMES:
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
    for value in (q05, q95):
        digest.update(np.ascontiguousarray(value, dtype=np.float64).tobytes())
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain an object")
    return value


def _arrays(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        return {
            name: np.array(archive[name], copy=True, order="C")
            for name in archive.files
        }


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def _assert_array(actual: np.ndarray, expected: np.ndarray, label: str) -> None:
    if not np.array_equal(np.asarray(actual), np.asarray(expected)):
        raise ValueError(f"independent replay mismatch: {label}")


def review(
    *,
    repo: Path,
    implementation_head: str,
    contract_root: str,
    contract_review_root: str,
    preflight_root: str,
    preflight_review_root: str,
    replay_root: str,
    output: Path = OUTPUT,
) -> str:
    if (
        sys.executable != "/root/autodl-tmp/dp312_venv/bin/python"
        or sys.version_info[:3] != (3, 12, 3)
        or sys.prefix != "/root/autodl-tmp/dp312_venv"
    ):
        raise RuntimeError("selector replay reviewer Python authority drifted")
    if (
        output != OUTPUT
        or output.exists()
        or _git(repo, "rev-parse", "HEAD") != implementation_head
        or _git(repo, "rev-parse", "refs/remotes/origin/main")
        != implementation_head
        or _git(repo, "status", "--porcelain=v1", "--untracked-files=no")
        or _git(DP, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(DP, "status", "--porcelain=v1", "--untracked-files=no")
    ):
        raise RuntimeError("selector replay reviewer live authority drifted")
    for path, root, label in (
        (CONTRACT, contract_root, "selector replay contract"),
        (CONTRACT_REVIEW, contract_review_root, "selector replay contract review"),
        (PREFLIGHT, preflight_root, "selector replay preflight"),
        (
            PREFLIGHT_REVIEW,
            preflight_review_root,
            "selector replay preflight review",
        ),
        (REPLAY, replay_root, "selector replay"),
        (CORRECTED_RAW, ROOTS["corrected_raw"], "corrected raw"),
        (
            CORRECTED_RAW_REVIEW,
            ROOTS["corrected_raw_review"],
            "corrected raw review",
        ),
        (TRAINING, ROOTS["training"], "accepted training"),
        (TRAINING_REVIEW, ROOTS["training_review"], "accepted training review"),
    ):
        verify_complete_seal(path, root, label=label)
    preflight = _json(PREFLIGHT / "report.json")
    produced = _json(REPLAY / "report.json")
    receipts = [
        json.loads(line)
        for line in (REPLAY / "receipts.jsonl")
        .read_text(encoding="ascii")
        .splitlines()
        if line
    ]
    if (
        len(receipts) != 320
        or produced.get("completed_slot_count") != 320
        or produced.get("state_count") != 64
        or produced.get("repeats_per_state") != 5
        or produced.get("formal_model_call_count") != 0
        or produced.get("dp_call_count") != 0
        or produced.get("latent_generation_call_count") != 0
        or produced.get("candidate_generation_call_count") != 0
        or produced.get("selector_call_count") != 640
        or produced.get("tensor_mutation_count") != 0
        or produced.get("fresh_or_holdout_outcome_read") is not False
        or produced.get("old_artifact_or_cas_write") is not False
        or produced.get("claim_authorized") is not False
    ):
        raise ValueError("selector replay report denominator/call drifted")
    assets = _arrays(PREFLIGHT / "selector_assets.npz")
    expected_asset_keys = {
        "atom_scales",
        "static14d_weights",
        "scene14d_theta",
        "context_q05",
        "context_q95",
    }
    if set(assets) != expected_asset_keys:
        raise ValueError("selector replay reviewer asset keyset drifted")
    scales = np.asarray(assets["atom_scales"], dtype=np.float64)
    static_weights = np.asarray(
        assets["static14d_weights"], dtype=np.float64
    )
    theta = np.asarray(assets["scene14d_theta"], dtype=np.float64)
    q05 = np.asarray(assets["context_q05"], dtype=np.float64)
    q95 = np.asarray(assets["context_q95"], dtype=np.float64)
    reviewed = []
    by_state: dict[int, list[dict[str, Any]]] = {}
    for slot, receipt in enumerate(receipts):
        binding = preflight["slot_receipts"][slot]
        raw_run = CORRECTED_RAW / "runs" / f"{slot:03d}"
        candidate = np.fromfile(
            raw_run / "candidate.f32le", dtype="<f4"
        ).reshape(8, 80, 4)
        neighbor = np.fromfile(
            raw_run / "neighbor.f32le", dtype="<f4"
        ).reshape(8, 32, 80, 4)
        candidate_sha = _array_sha(candidate)
        neighbor_sha = _array_sha(neighbor)
        validate_slot_authority(
            receipt=receipt,
            binding=binding,
            candidate=candidate,
            neighbor=neighbor,
        )
        if (
            receipt.get("receipt_sha256")
            != _sha(
                _canonical(
                    {
                        key: value
                        for key, value in receipt.items()
                        if key != "receipt_sha256"
                    }
                )
            )
        ):
            raise ValueError(f"selector replay slot authority drifted: {slot}")
        causal = _arrays(
            PREFLIGHT
            / preflight["state_receipts"][binding["state_index"]][
                "causal_input_relpath"
            ]
        )
        atom = literal_atoms(
            candidates=candidate, neighbor=neighbor, causal=causal
        )
        context = literal_context(
            candidates=candidate,
            causal=causal,
            source_valid_mask=atom["source_valid_mask"],
        )
        scene = literal_scene_weights(
            raw_context=context["raw"],
            source_complete=context["source_complete"],
            q05=q05,
            q95=q95,
            theta=theta,
        )
        static = literal_selection(
            candidates=candidate,
            raw_atoms=atom["raw_atoms"],
            scales=scales,
            weights=static_weights,
            eligibility_mask=atom["source_valid_mask"],
        )
        scene_selection = literal_selection(
            candidates=candidate,
            raw_atoms=atom["raw_atoms"],
            scales=scales,
            weights=scene["weights"],
            eligibility_mask=atom["source_valid_mask"],
        )
        preimage = _arrays(
            REPLAY / "slots" / f"{slot:03d}" / "selector_preimage.npz"
        )
        _assert_array(preimage["raw_atoms"], atom["raw_atoms"], "raw atoms")
        _assert_array(
            preimage["scaled_atoms"],
            atom["raw_atoms"] / scales[None, :],
            "scaled atoms",
        )
        _assert_array(
            preimage["clipped_atoms"],
            np.clip(atom["raw_atoms"] / scales[None, :], 0.0, 10.0),
            "clipped atoms",
        )
        for key in (
            "atom_source_valid_mask",
            "atom_applicable_mask",
            "source_valid_mask",
            "physical_feasible_mask",
        ):
            _assert_array(preimage[key], atom[key], key)
        _assert_array(preimage["static_weights"], static_weights, "static weights")
        _assert_array(
            preimage["static_scores"],
            np.asarray(static["scores"]),
            "static scores",
        )
        _assert_array(
            preimage["scene_context_raw"], context["raw"], "scene context"
        )
        _assert_array(
            preimage["scene_context_source_complete"],
            context["source_complete"],
            "scene context source-complete",
        )
        _assert_array(preimage["scene_phi"], scene["phi"], "scene phi")
        _assert_array(
            preimage["scene_weights"], scene["weights"], "scene weights"
        )
        _assert_array(
            preimage["scene_scores"],
            np.asarray(scene_selection["scores"]),
            "scene scores",
        )
        _assert_array(
            preimage["static_selected_action"],
            candidate[static["selected_index"]],
            "static action",
        )
        _assert_array(
            preimage["scene_selected_action"],
            candidate[scene_selection["selected_index"]],
            "scene action",
        )
        _assert_array(preimage["candidate0_action"], candidate[0], "candidate0")
        if (
            receipt.get("atom_receipt_sha256")
            != _array_sha(atom["raw_atoms"])
            or receipt.get("atom_availability") != atom["availability"]
            or receipt.get("atom_source_valid_mask")
            != atom["atom_source_valid_mask"].tolist()
            or receipt.get("atom_applicable_mask")
            != atom["atom_applicable_mask"].tolist()
            or receipt.get("physical_feasible_mask")
            != atom["physical_feasible_mask"].tolist()
            or receipt.get("context") != context["payload"]
            or receipt.get("context_receipt_sha256")
            != _sha(_canonical(context["payload"]))
            or receipt.get("candidate0")
            != {
                "selection_rule": "immutable_candidate_tensor_row0",
                "selected_index": 0,
                "selected_action_sha256": _array_sha(candidate[0]),
            }
        ):
            raise ValueError(f"selector replay atom/context drifted: {slot}")
        for arm, expected in (
            ("static14d", static),
            ("scene14d", scene_selection),
        ):
            produced_arm = receipt.get(arm)
            if (
                type(produced_arm) is not dict
                or produced_arm.get("arm")
                != ("Static14D" if arm == "static14d" else "Scene14D")
                or produced_arm.get("production_status") != "ok"
                or produced_arm.get("production_eligibility_mask_name")
                != "source_valid_mask"
                or produced_arm.get("production_score_contract")
                != "score_k=clip(a_k/s,0,10)^T w"
                or produced_arm.get("production_tie_break_contract")
                != "lowest_eligible_candidate_index"
            ):
                raise ValueError(f"selector replay {arm} metadata drifted")
            for key, value in expected.items():
                if produced_arm.get(key) != value:
                    raise ValueError(
                        f"selector replay {arm}.{key} drifted: {slot}"
                    )
        scene_receipt = receipt.get("scene_weight_receipt")
        if (
            type(scene_receipt) is not dict
            or scene_receipt.get("schema_version")
            != "camp_dp_v25_scene_weight_receipt_v3"
            or scene_receipt.get("model_name") != "CAMP-Scene14D"
            or scene_receipt.get("fixed_dp_head") != FIXED_DP_HEAD
            or scene_receipt.get("training_root_sha256") != ROOTS["training"]
            or scene_receipt.get("training_review_root_sha256")
            != ROOTS["training_review"]
            or scene_receipt.get("theta_sha256") != _array_sha(theta)
            or scene_receipt.get("context_scaler_sha256")
            != _context_scaler_sha(q05, q95)
            or scene_receipt.get("phi_sha256") != _array_sha(scene["phi"])
            or scene_receipt.get("weights_sha256")
            != _array_sha(scene["weights"])
            or scene_receipt.get("weights") != scene["weights"].tolist()
            or scene_receipt.get("runtime_projection") is not False
            or scene_receipt.get("softmax") is not False
        ):
            raise ValueError(f"selector replay scene receipt drifted: {slot}")
        reviewed.append(receipt)
        by_state.setdefault(int(receipt["state_index"]), []).append(receipt)
    if set(by_state) != set(range(64)):
        raise ValueError("selector replay state denominator drifted")
    for state_index, state_rows in by_state.items():
        try:
            verify_same_state(state_rows)
        except ValueError as exc:
            raise ValueError(
                f"selector replay state nondeterminism: {state_index}"
            ) from exc
    if (
        produced.get("status") != "PASS_runtime_selector_compatibility"
        or produced.get("typed_failure_count") != 0
        or produced.get("typed_failures") != []
        or produced.get("nondeterministic_state_count") != 0
        or produced.get("nondeterministic_states") != []
    ):
        raise ValueError("selector replay PASS boundary drifted")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent)
    )
    try:
        report = {
            "schema_version": (
                "camp_dp_v25_selector_after_pool_replay_review_v3"
            ),
            "status": "PASS_independent_literal_selector_replay_review",
            "reviewed_replay_root_sha256": replay_root,
            "reviewed_slot_count": len(reviewed),
            "reviewed_state_count": len(by_state),
            "reviewed_repeat_count_per_state": 5,
            "candidate0_row0_receipt_count": 320,
            "static14d_receipt_count": 320,
            "scene14d_receipt_count": 320,
            "independent_atom_reconstruction": True,
            "independent_context_and_scene_weight_reconstruction": True,
            "independent_score_mask_tie_index_action_reconstruction": True,
            "producer_metric_selector_or_decision_oracle_imported": False,
            "formal_model_call_count": 0,
            "dp_call_count": 0,
            "latent_generation_call_count": 0,
            "candidate_generation_call_count": 0,
            "selector_receipt_count": 640,
            "tensor_mutation_count": 0,
            "typed_failure_count": 0,
            "nondeterministic_state_count": 0,
            "fresh_or_holdout_outcome_read": False,
            "old_artifact_or_cas_write": False,
            "claim_authorized": False,
        }
        (staging / "report.json").write_bytes(_canonical(report))
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(
            staging, label="V25 selector-after-pool replay review"
        )
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 selector-after-pool replay review"
        )
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--implementation-head", required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--preflight-root", required=True)
    parser.add_argument("--preflight-review-root", required=True)
    parser.add_argument("--replay-root", required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(
        review(
            repo=args.repo,
            implementation_head=args.implementation_head,
            contract_root=args.contract_root,
            contract_review_root=args.contract_review_root,
            preflight_root=args.preflight_root,
            preflight_review_root=args.preflight_review_root,
            replay_root=args.replay_root,
            output=args.output,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
