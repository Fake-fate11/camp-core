#!/usr/bin/env python3
"""Independently review the bounded V25 R0 3x64 red K8 preflight."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (  # noqa: E402
    canonical_json_sha256,
    validate_runtime_signal_receipt,
    validate_signal_chain,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_scenario_phase import (  # noqa: E402
    _load_json,
    _write_json,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (  # noqa: E402
    CORPUS_STEPS,
    _git_head,
    _tracked_dirty,
)


SCHEMA_VERSION = "camp_dp_v25_r0_red_sequential_k8_review_v1"
SOURCE_SCHEMA_VERSION = "camp_dp_v25_r0_red_sequential_k8_preflight_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-artifact", type=Path, required=True)
    parser.add_argument("--preflight-root-sha256", required=True)
    parser.add_argument("--r0-source-artifact", type=Path, required=True)
    parser.add_argument("--r0-source-root-sha256", required=True)
    parser.add_argument("--r0-review-artifact", type=Path, required=True)
    parser.add_argument("--r0-review-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def review(args: argparse.Namespace) -> dict[str, Any]:
    head = _git_head(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree is dirty")
    preflight_seal = verify_complete_seal(
        args.preflight_artifact,
        args.preflight_root_sha256,
        label="V25 R0 red K8 preflight",
    )
    source_seal = verify_complete_seal(
        args.r0_source_artifact,
        args.r0_source_root_sha256,
        label="V25 R0 source",
    )
    source_review_seal = verify_complete_seal(
        args.r0_review_artifact,
        args.r0_review_root_sha256,
        label="V25 R0 source review",
    )
    for artifact in (
        args.preflight_artifact,
        args.r0_source_artifact,
        args.r0_review_artifact,
    ):
        if (artifact / "run.exit").read_text(encoding="ascii") != "0\n":
            raise ValueError("R0 input run.exit is not zero")
    report = _load_json(args.preflight_artifact / "report.json")
    probe_payload = _load_json(args.preflight_artifact / "probe_results.json")
    selector = _load_json(args.preflight_artifact / "selector_contract.json")
    chains = _load_json(args.r0_source_artifact / "red_signal_chains.json").get(
        "chains"
    )
    source_review = _load_json(args.r0_review_artifact / "report.json")
    results = probe_payload.get("results")
    if (
        report.get("schema_version") != SOURCE_SCHEMA_VERSION
        or report.get("status") != "passed_bounded_3x64_full_r_closed"
        or report.get("camp_head") != head
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("r0_source_root_sha256") != source_seal["root_sha256"]
        or report.get("r0_review_root_sha256")
        != source_review_seal["root_sha256"]
        or source_review.get("reviewed_root_sha256") != source_seal["root_sha256"]
        or report.get("selector_contract_sha256")
        != canonical_json_sha256(selector)
        or report.get("full_r_authorized") is not False
        or report.get("fresh_b2_opened") is not False
        or not isinstance(results, list)
        or len(results) != 3
        or not isinstance(chains, list)
        or len(chains) != 21
    ):
        raise ValueError("R0 red K8 preflight authority drifted")
    scales = np.asarray(selector.get("scales"), dtype=np.float64)
    weights = np.asarray(selector.get("weights"), dtype=np.float64)
    if (
        scales.shape != (14,)
        or weights.shape != (14,)
        or not np.isfinite(scales).all()
        or not np.isfinite(weights).all()
        or np.any(scales <= 0.0)
        or np.any(weights < 0.0)
        or not np.isclose(weights.sum(), 1.0, rtol=0.0, atol=1e-12)
        or selector.get("eligibility") != "source_valid"
    ):
        raise ValueError("R0 selector contract is invalid")
    chain_by_id = {str(chain["scenario_id"]): validate_signal_chain(chain) for chain in chains}
    reviewed = []
    for result in results:
        scenario_id = str(result.get("scenario_id"))
        chain = chain_by_id.get(scenario_id)
        rows = result.get("tick_fingerprints")
        if (
            chain is None
            or result.get("source_chain_sha256") != chain["source_chain_sha256"]
            or result.get("semantic_clone_sha256") != chain["semantic_clone_sha256"]
            or not isinstance(rows, list)
            or len(rows) != CORPUS_STEPS
            or result.get("tick_fingerprint_root_sha256")
            != canonical_json_sha256(rows)
        ):
            raise ValueError("R0 result/source-chain or 64-tick denominator drifted")
        selected = []
        all_k_high_risk = 0
        for tick_index, row in enumerate(rows):
            payload = {
                key: value for key, value in row.items() if key != "fingerprint_sha256"
            }
            raw = np.asarray(row.get("raw_atom_matrix"), dtype=np.float64)
            source_valid = np.asarray(row.get("source_valid_mask"), dtype=bool)
            physical = np.asarray(row.get("physical_feasible_mask"), dtype=bool)
            if (
                row.get("tick_index") != tick_index
                or row.get("fingerprint_sha256") != canonical_json_sha256(payload)
                or raw.shape != (8, 14)
                or source_valid.shape != (8,)
                or physical.shape != (8,)
                or not np.isfinite(raw).all()
                or np.any(raw < 0.0)
                or np.any(physical & ~source_valid)
                or not source_valid.any()
            ):
                raise ValueError("R0 fingerprint/mask/raw atom contract drifted")
            normalized = np.clip(raw / scales.reshape(1, 14), 0.0, 10.0)
            scores = normalized @ weights
            expected = int(np.argmin(np.where(source_valid, scores, np.inf)))
            signal_receipt = row.get("runtime_signal_receipt")
            validate_runtime_signal_receipt(signal_receipt, chain)
            if (
                row.get("selected_index") != expected
                or not np.array_equal(
                    np.asarray(row.get("production_scores"), dtype=np.float64),
                    scores,
                )
                or row.get("candidate0_sha256") != row.get("default_output_sha256")
                or row.get("candidate0_sha256")
                != row.get("candidate_row_sha256", [None])[0]
                or row.get("runtime_signal_receipt_sha256")
                != canonical_json_sha256(signal_receipt)
                or row.get("source_chain_sha256") != chain["source_chain_sha256"]
                or row.get("semantic_clone_sha256") != chain["semantic_clone_sha256"]
            ):
                raise ValueError("R0 independent score/index/signal binding mismatch")
            selected.append(expected)
            all_k_high_risk += int(bool(row.get("all_k_high_risk")))
        if result.get("selected_sequence_sha256") != canonical_json_sha256(selected):
            raise ValueError("R0 selected sequence hash mismatch")
        reviewed.append(
            {
                "scenario_id": scenario_id,
                "tier": result["tier"],
                "tick_count": len(rows),
                "all_k_high_risk_tick_count": all_k_high_risk,
                "selected_sequence_sha256": result["selected_sequence_sha256"],
                "fingerprint_root_sha256": result["tick_fingerprint_root_sha256"],
            }
        )
    if sorted(row["tier"] for row in reviewed) != ["borderline", "easy", "high_risk"]:
        raise ValueError("R0 review does not cover one identity per red tier")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_3x64_review_full_r_closed",
        "review_head": head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(args.preflight_artifact),
        "reviewed_root_sha256": preflight_seal["root_sha256"],
        "r0_source_root_sha256": source_seal["root_sha256"],
        "r0_source_review_root_sha256": source_review_seal["root_sha256"],
        "probe_count": len(reviewed),
        "probe_tick_count": sum(row["tick_count"] for row in reviewed),
        "probes": reviewed,
        "independent_scalar_clip_affine_argmin": True,
        "runtime_signal_receipts_independently_bound": True,
        "candidate0_operational_default_alias": True,
        "full_r_authorized": False,
        "full_r_started": False,
        "monitor_started": False,
        "training_executed": False,
        "calibration_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        report = review(args)
        _write_json(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_text(
            f"camp_head={report['review_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        root = seal_artifact(args.output_dir, label="V25 R0 red K8 review")
        print(json.dumps({"status": report["status"], "root_sha256": root}, sort_keys=True))
    except BaseException as exc:
        _write_json(
            args.output_dir / "failure.json",
            {
                "schema_version": SCHEMA_VERSION,
                "status": "failed",
                "failure_type": type(exc).__name__,
                "failure_reason": str(exc),
                "full_r_started": False,
                "fresh_b2_opened": False,
                "outcome_fields_consumed": [],
            },
        )
        (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
        seal_artifact(args.output_dir, label="V25 failed R0 red K8 review")
        raise


if __name__ == "__main__":
    main()
