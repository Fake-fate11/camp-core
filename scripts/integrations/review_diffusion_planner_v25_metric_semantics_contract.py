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


SOURCE_SCHEMA = "camp_dp_v25_metric_semantics_amendment_contract_artifact_v1"
SOURCE_STATUS = "sealed_outcome_independent_metric_semantics_contract"
REVIEW_SCHEMA = "camp_dp_v25_metric_semantics_amendment_contract_review_v1"
EXPECTED_CLASSES = {
    "safety_cost": "benchmark-only",
    "collision": "benchmark-only",
    "near_miss": "FAIL-industrial",
    "offroad": "FAIL-industrial",
    "wrong_way": "FAIL-industrial",
    "red_light_source_authority": "PASS",
    "red_light_outcome_aggregate": "benchmark-only",
    "speed": "benchmark-only",
    "progress_completion": "benchmark-only",
    "jerk": "FAIL-industrial",
    "lateral_acceleration": "FAIL-industrial",
    "maximum_deceleration": "FAIL-industrial",
    "latency_measurement": "benchmark-only",
    "online_production_readiness": "FAIL-industrial",
    "clustered_statistics": "PASS",
    "full_polygon_offroad": "evidence-missing",
    "occupant_seat_vertical_comfort": "evidence-missing",
}


def review(*, source: Path, source_root: str, output: Path) -> str:
    verify_complete_seal(source, source_root, label="metric-semantics contract")
    report = _object(source / "report.json")
    if (
        report.get("schema_version") != SOURCE_SCHEMA
        or report.get("status") != SOURCE_STATUS
        or report.get("outcome_values_read") is not False
        or report.get("sealed_execution_written") is not False
        or report.get("scientific_or_continuation_cas_written") is not False
    ):
        raise ValueError("metric-semantics contract artifact invariant drifted")
    contract = report.get("contract")
    if type(contract) is not dict:
        raise ValueError("metric-semantics contract payload missing")
    if (
        contract.get("schema_version")
        != "camp_dp_v25_metric_semantics_amendment_contract_v1"
        or contract.get("status")
        != "frozen_outcome_independent_metric_semantics_contract"
        or contract.get("outcome_independent") is not True
        or contract.get("metric_classifications") != EXPECTED_CLASSES
    ):
        raise ValueError("metric-semantics literal classification oracle failed")
    body = contract.get("body_proxy")
    if (
        type(body) is not dict
        or body.get("dt_s") != 0.1
        or body.get("tick_count") != 64
        or body.get("raw_acceleration_count") != 62
        or body.get("filter", {}).get("width_samples") != 11
        or body.get("filter", {}).get("filtered_sample_count") != 52
        or body.get("filter", {}).get("valid_only") is not True
        or body.get("filter", {}).get("padding") is not False
        or body.get("per_run_before_pair_and_cluster") is not True
        or body.get("new_ni_or_claim_gate") is not False
    ):
        raise ValueError("metric-semantics body-proxy literal oracle failed")
    missing = contract.get("missing_evidence")
    if (
        type(missing) is not dict
        or missing.get("full_polygon_offroad") != "evidence_missing"
        or missing.get("vertical_acceleration") != "not_modeled"
        or missing.get("iso_2631_conformity") != "not_assessed"
        or missing.get("sae_j2834_conformity") != "not_assessed"
        or missing.get("industrial_occupant_comfort")
        != "evidence_missing_not_assessed"
    ):
        raise ValueError("metric-semantics missing-evidence oracle failed")
    claim = contract.get("claim_invariance")
    if (
        type(claim) is not dict
        or claim.get("new_confirmatory_claim_authorized") is not False
        or claim.get("final_claim_decision")
        != "honest_no_claim_under_frozen_preregistered_all_gate"
        or claim.get("promotion_or_deployment_authorized") is not False
    ):
        raise ValueError("metric-semantics claim-invariance oracle failed")
    legacy = contract.get("legacy_namespace")
    if type(legacy) is not dict or len(legacy) != 14 or any(
        type(item) is not dict
        or item.get("deprecated_industrial_interpretation") is not True
        or type(item.get("accurate_alias")) is not str
        or type(item.get("formula")) is not str
        for item in legacy.values()
    ):
        raise ValueError("metric-semantics legacy literal oracle failed")
    implementation = report.get("implementation")
    if (
        type(implementation) is not dict
        or implementation.get("git_head") != _git_head()
        or implementation.get("tracked_clean") is not True
    ):
        raise ValueError("metric-semantics contract implementation drifted")
    review_report = {
        "schema_version": REVIEW_SCHEMA,
        "status": "passed_independent_outcome_free_contract_review",
        "source": {"path": str(source.resolve()), "root_sha256": source_root},
        "reviewer_role": "separate_literal_contract_oracle",
        "producer_validator_imported": False,
        "outcome_values_read": False,
        "classification_matrix_rebuilt": True,
        "body_formula_and_sample_accounting_rebuilt": True,
        "legacy_alias_formula_set_rebuilt": True,
        "missing_evidence_fail_closed": True,
        "claim_invariance_verified": True,
        "sealed_execution_written": False,
        "scientific_or_continuation_cas_written": False,
        "review_head": _git_head(),
    }
    return _write_atomic(output, review_report)


def _write_atomic(output: Path, report: dict[str, Any]) -> str:
    output = output.resolve()
    if output.exists():
        raise ValueError("metric-semantics contract review output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(_canonical_bytes(report))
        (staging / "HEADS.json").write_bytes(
            _canonical_bytes(
                {"role": "metric_semantics_contract_review", "head": _git_head()}
            )
        )
        root = seal_artifact(staging, label="V25 metric-semantics contract review")
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 metric-semantics contract review"
        )
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain an object")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    print(review(source=args.source, source_root=args.source_root, output=args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
