#!/usr/bin/env python3
"""Independently rebuild a sealed V25 final evidence package."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_final_delivery import (  # noqa: E402
    FIXED_DP_HEAD,
    REQUIRED_ARTIFACT_ROLES,
    build_v25_final_delivery_evidence,
    validate_v25_final_delivery_input_manifest,
)
from scripts.integrations.build_diffusion_planner_v25_final_evidence import (  # noqa: E402
    BENCHMARK_A,
    BENCHMARK_A_SHA256,
    CONTRACT,
    CONTRACT_SHA256,
    SCHEMA_VERSION as ARTIFACT_SCHEMA_VERSION,
    _canonical_json,
    _git_head,
    _load_scientific_payloads,
    _sha256,
    _strict_json_object,
    _tracked_dirty,
    _verify_artifact_registry,
    _write_json,
)


SCHEMA_VERSION = "camp_dp_v25_final_evidence_review_v1"


def review_final_evidence_artifact(
    *, artifact: Path, artifact_root_sha256: str, output_dir: Path
) -> str:
    source = Path(artifact).resolve()
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree must be clean")
    seal = verify_complete_seal(
        source, artifact_root_sha256, label="V25 final evidence package"
    )
    if (source / "run.exit").read_bytes() != b"0\n":
        raise ValueError("V25 final evidence package did not exit successfully")
    report = _canonical_json(source / "report.json")
    recorded = _canonical_json(source / "final_evidence.json")
    manifest = validate_v25_final_delivery_input_manifest(
        _canonical_json(source / "input_manifest.json")
    )
    _validate_source_report(report, source=source)
    artifacts = _verify_artifact_registry(manifest["artifacts"])
    inputs = _load_scientific_payloads(artifacts)
    rebuilt = build_v25_final_delivery_evidence(
        contract=_strict_json_object(CONTRACT),
        contract_sha256=CONTRACT_SHA256,
        atom_audit=inputs["atom_audit"],
        training_report=inputs["training_report"],
        training_model_reports=inputs["training_model_reports"],
        auxiliary_report=inputs["auxiliary_report"],
        calibration_contract=inputs["calibration_contract"],
        preopen_qualification=inputs["preopen_qualification"],
        benchmark_a=_strict_json_object(BENCHMARK_A),
        benchmark_b_evaluation=inputs["benchmark_b_evaluation"],
        artifact_registry=manifest["artifacts"],
        camp_heads=manifest["camp_heads"],
        fixed_dp_head=manifest["fixed_dp_head"],
        fresh_open_count=manifest["fresh_open_count"],
    )
    if not _strict_equal(recorded, rebuilt):
        raise ValueError("V25 final evidence differs from independent reconstruction")
    expected_report_claims = rebuilt["method_claims"]
    if not _strict_equal(report["method_claims"], expected_report_claims):
        raise ValueError("V25 final report claim summary drifted")
    output.mkdir(parents=True)
    review_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_v25_final_evidence_review",
        "camp_head": _git_head(ROOT),
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(source),
        "reviewed_root_sha256": seal["root_sha256"],
        "contract_sha256": CONTRACT_SHA256,
        "benchmark_a_sha256": BENCHMARK_A_SHA256,
        "reviewed_artifact_role_count": len(artifacts),
        "reviewed_required_artifact_roles": list(REQUIRED_ARTIFACT_ROLES),
        "all_upstream_source_and_review_seals_reopened": True,
        "all_required_sections_independently_rebuilt": True,
        "method_claims_rebuilt_without_protocol_change": True,
        "final_decision": rebuilt["final_decision"],
        "promotion_deployment_activation_authorized": False,
    }
    _write_json(output / "report.json", review_report)
    (output / "HEADS").write_bytes(
        f"camp_head={review_report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n".encode(
            "ascii"
        )
    )
    (output / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(output, label="V25 final evidence package review")


def _validate_source_report(report: dict[str, Any], *, source: Path) -> None:
    expected_fields = {
        "schema_version",
        "status",
        "camp_head",
        "fixed_dp_head",
        "input_manifest_source",
        "input_manifest_sha256",
        "contract_sha256",
        "benchmark_a_sha256",
        "verified_artifact_role_count",
        "verified_required_artifact_roles",
        "final_evidence_sha256",
        "final_decision",
        "method_claims",
        "required_sections_complete",
        "fresh_b2_opened_exactly_once",
        "outcome_used_to_change_protocol",
        "promotion_deployment_activation_authorized",
    }
    if type(report) is not dict or set(report) != expected_fields:
        raise ValueError("V25 final evidence report field set drifted")
    if (
        report["schema_version"] != ARTIFACT_SCHEMA_VERSION
        or report["status"] != "sealed_v25_final_evidence_package"
        or report["camp_head"] != _git_head(ROOT)
        or report["fixed_dp_head"] != FIXED_DP_HEAD
        or report["input_manifest_sha256"] != _sha256(source / "input_manifest.json")
        or report["contract_sha256"] != CONTRACT_SHA256
        or report["benchmark_a_sha256"] != BENCHMARK_A_SHA256
        or report["verified_artifact_role_count"] < len(REQUIRED_ARTIFACT_ROLES)
        or report["verified_required_artifact_roles"] != list(REQUIRED_ARTIFACT_ROLES)
        or report["final_evidence_sha256"] != _sha256(source / "final_evidence.json")
        or report["required_sections_complete"] is not True
        or report["fresh_b2_opened_exactly_once"] is not True
        or report["outcome_used_to_change_protocol"] is not False
        or report["promotion_deployment_activation_authorized"] is not False
    ):
        raise ValueError("V25 final evidence report value drifted")


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--artifact-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    root = review_final_evidence_artifact(
        artifact=args.artifact,
        artifact_root_sha256=args.artifact_root_sha256,
        output_dir=args.output_dir,
    )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
