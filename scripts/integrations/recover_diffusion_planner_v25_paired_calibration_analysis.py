#!/usr/bin/env python3
"""Recover post-run calibration analysis from immutable sealed raw evidence."""

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
from camp_core.integrations.diffusion_planner_v25_calibration_analysis import (  # noqa: E402
    analyze_paired_calibration_outcomes,
)
from camp_core.integrations.diffusion_planner_v25_calibration_atoms import (  # noqa: E402
    analyze_calibration_decision_evidence,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    load_v25_runtime_selector_assets,
)
from scripts.integrations.run_diffusion_planner_v25_candidate0_calibration import (  # noqa: E402
    _canonical_json,
    _sha256,
    _write_json,
)
from scripts.integrations.run_diffusion_planner_v25_paired_calibration import (  # noqa: E402
    _camp_decision_runs,
)


SCHEMA_VERSION = "camp_dp_v25_paired_calibration_recovery_analysis_v1"
FAILED_EXECUTION_ROOT = (
    "5cd071b6ac9dd805422d7fe572f3db273abe9fce5cd4f910a0cf6fa9296e8249"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_FAILURE = {
    "schema_version": "camp_dp_v25_paired_calibration_execution_artifact_v1",
    "status": "failed_closed_paired_calibration_execution",
    "reason": "unregistered calibration latency fields: ['input_materialization']",
    "fresh_b2_opened": False,
    "outcome_fields_consumed": [],
}


def recover(
    *,
    failed_artifact: Path,
    failed_root_sha256: str,
    localization_receipt: Path,
    localization_receipt_sha256: str,
    probe_template: Path,
    probe_template_sha256: str,
    output_dir: Path,
) -> str:
    failed = failed_artifact.resolve()
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    if failed_root_sha256 != FAILED_EXECUTION_ROOT:
        raise ValueError("unexpected failed calibration root")
    failed_seal = verify_complete_seal(
        failed, failed_root_sha256, label="failed paired calibration raw evidence"
    )
    if (failed / "run.exit").read_bytes() != b"1\n":
        raise ValueError("original calibration failure exit drifted")
    if _canonical_json(failed / "failure.json") != EXPECTED_FAILURE:
        raise ValueError("original calibration failure receipt drifted")

    receipt_path = localization_receipt.resolve()
    if _sha256(receipt_path) != localization_receipt_sha256:
        raise ValueError("localization receipt SHA drifted")
    localization = _canonical_json(receipt_path)
    _validate_localization(localization, failed_root_sha256)
    roots = dict(localization["input_root_bindings"])
    for role in (
        "map",
        "paired_plan",
        "paired_plan_review",
        "plan",
        "preregistration",
        "preregistration_review",
        "route",
        "route_review",
        "runtime",
        "runtime_review",
        "training",
        "training_review",
    ):
        verify_complete_seal(
            Path(roots[f"{role}_artifact"]),
            roots[f"{role}_root_sha256"],
            label=f"recovery input {role}",
        )
    if _sha256(probe_template.resolve()) != probe_template_sha256:
        raise ValueError("probe-template SHA drifted")

    corpus = _canonical_json(failed / "paired_calibration_corpus.json")
    if (
        corpus.get("terminal_arm_run_count") != 300
        or corpus.get("complete_arm_run_count") != 300
        or corpus.get("paired_eligible_pair_count") != 100
        or corpus.get("coverage_gate_passed") is not True
    ):
        raise ValueError("sealed calibration denominator is not recoverable")
    analysis = analyze_paired_calibration_outcomes(corpus)
    assets = load_v25_runtime_selector_assets(
        training_artifact=Path(roots["training_artifact"]),
        training_root_sha256=roots["training_root_sha256"],
        training_review_artifact=Path(roots["training_review_artifact"]),
        training_review_root_sha256=roots["training_review_root_sha256"],
    )
    atoms = analyze_calibration_decision_evidence(
        camp_runs=_camp_decision_runs(output=failed, corpus=corpus),
        atom_scales=assets.atom_scales,
        static14d_weights=assets.static14d_weights,
        scene14d_provider=assets.scene14d_weight_provider,
        training_artifact=Path(roots["training_artifact"]),
    )

    output.mkdir(parents=True)
    _write_json(output / "calibration_analysis.json", analysis)
    _write_json(output / "atom_calibration.json", atoms)
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "recovered_calibration_analysis_complete_fresh_closed",
        "camp_head": _git_head(ROOT),
        "fixed_dp_head": FIXED_DP_HEAD,
        "original_execution_artifact": str(failed),
        "original_execution_root_sha256": failed_seal["root_sha256"],
        "original_execution_run_exit": 1,
        "original_terminal_analysis_failure": EXPECTED_FAILURE["reason"],
        "original_raw_evidence_modified": False,
        "localization_receipt": str(receipt_path),
        "localization_receipt_sha256": localization_receipt_sha256,
        "input_roots": roots,
        "probe_template": str(probe_template.resolve()),
        "probe_template_sha256": probe_template_sha256,
        "terminal_arm_run_count": 300,
        "complete_arm_run_count": 300,
        "paired_eligible_pair_count": 100,
        "native_tick_count": 19_200,
        "input_materialization_latency_count": localization[
            "input_materialization"
        ]["total_count"],
        "input_materialization_classification": "supplementary_runtime_latency",
        "calibration_analysis_sha256": _sha256(
            output / "calibration_analysis.json"
        ),
        "atom_calibration_sha256": _sha256(output / "atom_calibration.json"),
        "model_or_threshold_changed": False,
        "raw_outcome_or_selection_changed": False,
        "independent_review_completed": False,
        "accepted_as_fresh_or_claim_evidence": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    _write_json(output / "report.json", report)
    (output / "HEADS").write_text(
        f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (output / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output / "run.exit").write_text("0\n", encoding="ascii")
    return seal_artifact(output, label="V25 paired calibration recovery analysis")


def _validate_localization(value: Mapping[str, Any], root: str) -> None:
    required = {
        "schema_version": "camp_dp_v25_calibration_readonly_localization_receipt_v1",
        "classification": "A_terminal_analyzer_latency_registry_harness_defect",
        "execution_root_sha256": root,
        "run_exit": 1,
        "terminal_arm_run_count": 300,
        "complete_arm_run_count": 300,
        "paired_eligible_pair_count": 100,
        "native_tick_count": 19_200,
        "recorded_corpus_reconstructed_exact": True,
        "all_run_configs_rebuilt_exact": True,
        "all_terminal_rows_bound_exact": True,
        "all_native_receipts_revalidated": True,
        "all_initial_pair_resets_rechecked": True,
        "all_outcome_rows_reconstructed_from_sealed_raw_evidence": True,
        "all_atom_rows_recomputed_from_sealed_decision_evidence": True,
        "full_analysis_succeeds_when_existing_timing_is_registered": True,
        "accepted_as_fresh_or_claim_evidence": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    for name, expected in required.items():
        if type(value.get(name)) is not type(expected) or value.get(name) != expected:
            raise ValueError(f"localization receipt field {name} drifted")
    latency = value.get("input_materialization")
    if (
        type(latency) is not dict
        or latency.get("unit") != "milliseconds"
        or latency.get("json_python_type") != "float"
        or latency.get("total_count") != 19_200
        or any(row.get("finite_count") != 6_400 for row in latency["per_arm"].values())
    ):
        raise ValueError("localized input-materialization coverage drifted")


def _git_head(root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--failed-artifact", type=Path, required=True)
    parser.add_argument("--failed-root-sha256", required=True)
    parser.add_argument("--localization-receipt", type=Path, required=True)
    parser.add_argument("--localization-receipt-sha256", required=True)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--probe-template-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = recover(**vars(args))
    print(json.dumps({"status": "sealed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
