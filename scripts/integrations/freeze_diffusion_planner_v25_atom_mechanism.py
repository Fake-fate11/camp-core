#!/usr/bin/env python3
"""Freeze outcome-blind Fresh-B2 atom-mechanism analysis over accepted calibration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_atom_mechanism import (  # noqa: E402
    MECHANISM_SUMMARY_STORAGE_UPPER_BOUND_BYTES,
    analyze_atom_mechanisms,
    validate_atom_mechanism_contract,
)
from camp_core.integrations.diffusion_planner_v25_calibration_analysis import (  # noqa: E402
    _project_complete,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    load_v25_runtime_selector_assets,
)
from scripts.integrations.run_diffusion_planner_v25_candidate0_calibration import (  # noqa: E402
    _canonical_json,
    _sha256,
    _write_json,
)


SCHEMA_VERSION = "camp_dp_v25_atom_mechanism_artifact_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def freeze(
    *,
    contract: Path,
    calibration_artifact: Path,
    calibration_root_sha256: str,
    recovery_artifact: Path,
    recovery_root_sha256: str,
    recovery_review_artifact: Path,
    recovery_review_root_sha256: str,
    training_artifact: Path,
    training_root_sha256: str,
    training_review_artifact: Path,
    training_review_root_sha256: str,
    storage_qualification_artifact: Path,
    storage_qualification_root_sha256: str,
    storage_review_artifact: Path,
    storage_review_root_sha256: str,
    output_dir: Path,
) -> str:
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree must be clean")
    calibration = calibration_artifact.resolve()
    recovery = recovery_artifact.resolve()
    recovery_review = recovery_review_artifact.resolve()
    training = training_artifact.resolve()
    training_review = training_review_artifact.resolve()
    storage = storage_qualification_artifact.resolve()
    storage_review = storage_review_artifact.resolve()
    verify_complete_seal(calibration, calibration_root_sha256, label="atom mechanism calibration raw")
    verify_complete_seal(recovery, recovery_root_sha256, label="atom mechanism recovery")
    verify_complete_seal(recovery_review, recovery_review_root_sha256, label="atom mechanism recovery review")
    verify_complete_seal(training, training_root_sha256, label="atom mechanism training")
    verify_complete_seal(training_review, training_review_root_sha256, label="atom mechanism training review")
    verify_complete_seal(storage, storage_qualification_root_sha256, label="atom mechanism storage qualification")
    verify_complete_seal(storage_review, storage_review_root_sha256, label="atom mechanism storage review")
    if (calibration / "run.exit").read_bytes() != b"1\n" or any(
        (path / "run.exit").read_bytes() != b"0\n"
        for path in (recovery, recovery_review, training, training_review)
    ):
        raise ValueError("atom-mechanism upstream terminal state drifted")
    if (storage / "run.exit").read_bytes() != b"0\n" or (storage_review / "run.exit").read_bytes() != b"0\n":
        raise ValueError("atom-mechanism storage qualification terminal state drifted")
    storage_report = _canonical_json(storage / "report.json")
    storage_review_report = _canonical_json(storage_review / "report.json")
    if (
        storage_report.get("status") != "passed_fresh_storage_equivalence_and_capacity"
        or storage_report.get("capacity_gate_passed") is not True
        or storage_report.get("fresh_b2_opened") is not False
        or storage_report.get("outcome_fields_consumed") != []
        or storage_review_report.get("status")
        != "passed_independent_fresh_storage_equivalence_and_capacity_review"
        or storage_review_report.get("reviewed_root_sha256")
        != storage_qualification_root_sha256
        or storage_review_report.get("capacity_gate_passed") is not True
        or storage_review_report.get("fresh_b2_opened") is not False
        or storage_review_report.get("outcome_fields_consumed") != []
    ):
        raise ValueError("atom-mechanism storage qualification receipt drifted")
    contract_path = contract.resolve()
    frozen_contract = validate_atom_mechanism_contract(_canonical_json(contract_path))
    corpus = _canonical_json(calibration / "paired_calibration_corpus.json")
    if (
        corpus.get("terminal_arm_run_count") != 300
        or corpus.get("complete_arm_run_count") != 300
        or corpus.get("paired_eligible_pair_count") != 100
        or corpus.get("coverage_gate_passed") is not True
    ):
        raise ValueError("atom-mechanism calibration denominator drifted")
    assets = load_v25_runtime_selector_assets(
        training_artifact=training,
        training_root_sha256=training_root_sha256,
        training_review_artifact=training_review,
        training_review_root_sha256=training_review_root_sha256,
    )
    decision_runs, references = _mechanism_runs(calibration, corpus)
    outcomes = _outcomes(corpus)
    analysis = analyze_atom_mechanisms(
        decision_runs=decision_runs,
        outcomes_by_unit=outcomes,
        atom_scales=assets.atom_scales,
        static14d_weights=assets.static14d_weights,
        scene14d_provider=assets.scene14d_weight_provider,
        training_artifact=training,
    )
    output.mkdir(parents=True)
    _write_json(output / "mechanism_contract.json", frozen_contract)
    _write_json(output / "calibration_atom_mechanism.json", analysis)
    _write_json(output / "evidence_references.json", references)
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "frozen_atom_mechanism_ready_before_fresh_b2_opening",
        "camp_head": _git_head(ROOT),
        "fixed_dp_head": FIXED_DP_HEAD,
        "calibration_artifact": str(calibration),
        "calibration_root_sha256": calibration_root_sha256,
        "calibration_run_exit": 1,
        "recovery_artifact": str(recovery),
        "recovery_root_sha256": recovery_root_sha256,
        "recovery_review_artifact": str(recovery_review),
        "recovery_review_root_sha256": recovery_review_root_sha256,
        "training_artifact": str(training),
        "training_root_sha256": training_root_sha256,
        "training_review_artifact": str(training_review),
        "training_review_root_sha256": training_review_root_sha256,
        "storage_qualification_artifact": str(storage),
        "storage_qualification_root_sha256": storage_qualification_root_sha256,
        "storage_review_artifact": str(storage_review),
        "storage_review_root_sha256": storage_review_root_sha256,
        "storage_projected_1500_arm_upper_bound_nbytes_before_mechanism": storage_report[
            "projected_1500_arm_upper_bound_nbytes"
        ],
        "mechanism_summary_storage_upper_bound_bytes": MECHANISM_SUMMARY_STORAGE_UPPER_BOUND_BYTES,
        "storage_projected_1500_arm_upper_bound_nbytes_with_mechanism": storage_report[
            "projected_1500_arm_upper_bound_nbytes"
        ] + MECHANISM_SUMMARY_STORAGE_UPPER_BOUND_BYTES,
        "fresh_storage_capacity_gate_passed": True,
        "contract_path": str(contract_path),
        "contract_sha256": _sha256(contract_path),
        "mechanism_contract_sha256": _sha256(output / "mechanism_contract.json"),
        "calibration_atom_mechanism_sha256": _sha256(output / "calibration_atom_mechanism.json"),
        "evidence_references_sha256": _sha256(output / "evidence_references.json"),
        "paired_unit_count": 100,
        "camp_run_count": len(decision_runs),
        "decision_tick_count": len(decision_runs) * 64,
        "raw_k8_payload_copied": False,
        "same_saved_fixed_k8_pool_used": True,
        "primary_fresh_design_changed": False,
        "model_or_weight_changed": False,
        "single_atom_closed_loop_causal_effect_claimed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
        "independent_review_completed": False,
    }
    _write_json(output / "report.json", report)
    (output / "HEADS").write_text(
        f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (output / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output / "run.exit").write_text("0\n", encoding="ascii")
    return seal_artifact(output, label="V25 Fresh B2 atom-mechanism preopen authority")


def _mechanism_runs(calibration: Path, corpus: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    result = []
    references = []
    for row in corpus["arm_results"]:
        if row["status"] != "complete" or row["plan_arm"] == "candidate0_operational_default":
            continue
        run_dir = calibration / "runs" / (
            f"{row['run_ordinal']:04d}_{row['unit_ordinal']:04d}_{row['arm_order_index']}_{row['plan_arm']}"
        )
        evidence_path = run_dir / "decision_evidence.json"
        evidence = _canonical_json(evidence_path)
        native = row["native_receipt"]
        evidence_sha = _sha256(evidence_path)
        if (
            type(evidence) is not list
            or len(evidence) != 64
            or native.get("calibration_decision_evidence_sha256") != evidence_sha
            or native.get("calibration_decision_evidence_count") != 64
        ):
            raise ValueError("atom-mechanism decision evidence binding drifted")
        result.append(
            {
                "plan_arm": row["plan_arm"],
                "unit_ordinal": row["unit_ordinal"],
                "corridor_sha256": row["corridor_sha256"],
                "snapshots": evidence,
                "native_ticks": native["ticks"],
                "scenario_family": row["scenario_family"],
                "risk_tier": row["risk_tier"],
                "signal_source_class": row["signal_source_class"],
                "phase_authority_mode": row["phase_authority_mode"],
            }
        )
        references.append(
            {
                "unit_ordinal": row["unit_ordinal"],
                "plan_arm": row["plan_arm"],
                "relative_path": evidence_path.relative_to(calibration).as_posix(),
                "logical_sha256": evidence_sha,
                "logical_bytes": evidence_path.stat().st_size,
                "raw_payload_copied": False,
            }
        )
    return result, references


def _outcomes(corpus: Mapping[str, Any]) -> dict[int, dict[str, Mapping[str, Any]]]:
    result: dict[int, dict[str, Mapping[str, Any]]] = {}
    for row in corpus["arm_results"]:
        if row["status"] != "complete":
            raise ValueError("atom-mechanism requires complete paired calibration")
        result.setdefault(row["unit_ordinal"], {})[row["plan_arm"]] = _project_complete(row)
    return result


def _git_head(path: Path) -> str:
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def _tracked_dirty(path: Path) -> bool:
    return bool(subprocess.check_output(["git", "-C", str(path), "status", "--short", "--untracked-files=no"], text=True).strip())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--calibration-artifact", type=Path, required=True)
    parser.add_argument("--calibration-root-sha256", required=True)
    parser.add_argument("--recovery-artifact", type=Path, required=True)
    parser.add_argument("--recovery-root-sha256", required=True)
    parser.add_argument("--recovery-review-artifact", type=Path, required=True)
    parser.add_argument("--recovery-review-root-sha256", required=True)
    parser.add_argument("--training-artifact", type=Path, required=True)
    parser.add_argument("--training-root-sha256", required=True)
    parser.add_argument("--training-review-artifact", type=Path, required=True)
    parser.add_argument("--training-review-root-sha256", required=True)
    parser.add_argument("--storage-qualification-artifact", type=Path, required=True)
    parser.add_argument("--storage-qualification-root-sha256", required=True)
    parser.add_argument("--storage-review-artifact", type=Path, required=True)
    parser.add_argument("--storage-review-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = freeze(**vars(args))
    print(json.dumps({"status": "sealed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
