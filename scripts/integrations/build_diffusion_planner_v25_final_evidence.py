#!/usr/bin/env python3
"""Build the V25 final evidence package from sealed reviewed artifacts."""

from __future__ import annotations

import argparse
import hashlib
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
from camp_core.integrations.diffusion_planner_v25_calibration_artifact import (  # noqa: E402
    validate_calibration_freeze_payload,
)
from camp_core.integrations.diffusion_planner_v25_final_delivery import (  # noqa: E402
    FIXED_DP_HEAD,
    REQUIRED_ARTIFACT_ROLES,
    build_v25_final_delivery_evidence,
    validate_v25_final_delivery_input_manifest,
)
from camp_core.integrations.diffusion_planner_v25_fresh_b2 import (  # noqa: E402
    validate_fresh_b2_preopen_qualification,
)


SCHEMA_VERSION = "camp_dp_v25_final_evidence_artifact_v1"
CONTRACT = (
    ROOT
    / "configs"
    / "integrations"
    / "diffusion_planner_v25_final_delivery_contract_v1.json"
)
CONTRACT_SHA256 = "b0db0c4ea76938658fe4e1f2987073c9ac326dee677004e470836eced111c26f"
BENCHMARK_A = (
    ROOT
    / "configs"
    / "integrations"
    / "diffusion_planner_v25_legacy_benchmark_a_v1.json"
)
BENCHMARK_A_SHA256 = "7adf068a1b3df6b7ff94bee3e4b14819b29f877b3f1c3d7ace64fdef47d58b72"

EXPECTED_REVIEW_STATUS_BY_ROLE = {
    "corrected_full_corpus": "passed_independent_full_corpus_review",
    "train_only_atom_audit": "passed_independent_train_only_atom_audit_review",
    "main_training": "passed_independent_strict_convex_training_review",
    "auxiliary_static14d_full": (
        "passed_independent_static14d_full_auxiliary_training_review"
    ),
    "calibration_freeze": "passed_independent_calibration_freeze_review",
    "power_pilot": "passed_independent_candidate0_power_pilot_review",
    "fresh_b2_preopen": "passed_independent_fresh_b2_preopen_review",
    "fresh_b2_execution": (
        "passed_independent_fresh_b2_three_arm_execution_review"
    ),
    "fresh_b2_evaluation": "passed_independent_fresh_b2_evaluation_review",
}
if set(EXPECTED_REVIEW_STATUS_BY_ROLE) != set(REQUIRED_ARTIFACT_ROLES):
    raise RuntimeError("V25 final review-status role registry drifted")


def build_final_evidence_artifact(*, input_manifest: Path, output_dir: Path) -> str:
    manifest_path = Path(input_manifest).resolve()
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree must be clean")
    manifest = validate_v25_final_delivery_input_manifest(
        _canonical_json(manifest_path)
    )
    if manifest["contract"] != {
        "path": CONTRACT.relative_to(ROOT).as_posix(),
        "sha256": CONTRACT_SHA256,
    }:
        raise ValueError("V25 final contract receipt drifted")
    if _sha256(CONTRACT) != CONTRACT_SHA256 or _sha256(BENCHMARK_A) != BENCHMARK_A_SHA256:
        raise ValueError("V25 frozen final-delivery config SHA drifted")
    if manifest["camp_heads"]["local"] != _git_head(ROOT):
        raise ValueError("V25 final input manifest does not match live CAMP HEAD")
    artifacts = _verify_artifact_registry(manifest["artifacts"])
    inputs = _load_scientific_payloads(artifacts)
    contract = _strict_json_object(CONTRACT)
    benchmark_a = _strict_json_object(BENCHMARK_A)
    evidence = build_v25_final_delivery_evidence(
        contract=contract,
        contract_sha256=CONTRACT_SHA256,
        atom_audit=inputs["atom_audit"],
        training_report=inputs["training_report"],
        training_model_reports=inputs["training_model_reports"],
        auxiliary_report=inputs["auxiliary_report"],
        calibration_contract=inputs["calibration_contract"],
        preopen_qualification=inputs["preopen_qualification"],
        benchmark_a=benchmark_a,
        benchmark_b_evaluation=inputs["benchmark_b_evaluation"],
        artifact_registry=manifest["artifacts"],
        camp_heads=manifest["camp_heads"],
        fixed_dp_head=manifest["fixed_dp_head"],
        fresh_open_count=manifest["fresh_open_count"],
    )
    output.mkdir(parents=True)
    _write_json(output / "input_manifest.json", manifest)
    _write_json(output / "final_evidence.json", evidence)
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "sealed_v25_final_evidence_package",
        "camp_head": _git_head(ROOT),
        "fixed_dp_head": FIXED_DP_HEAD,
        "input_manifest_source": str(manifest_path),
        "input_manifest_sha256": _sha256(output / "input_manifest.json"),
        "contract_sha256": CONTRACT_SHA256,
        "benchmark_a_sha256": BENCHMARK_A_SHA256,
        "verified_artifact_role_count": len(artifacts),
        "verified_required_artifact_roles": list(REQUIRED_ARTIFACT_ROLES),
        "final_evidence_sha256": _sha256(output / "final_evidence.json"),
        "final_decision": evidence["final_decision"],
        "method_claims": evidence["method_claims"],
        "required_sections_complete": True,
        "fresh_b2_opened_exactly_once": True,
        "outcome_used_to_change_protocol": False,
        "promotion_deployment_activation_authorized": False,
    }
    _write_json(output / "report.json", report)
    (output / "HEADS").write_bytes(
        f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n".encode(
            "ascii"
        )
    )
    (output / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(output, label="V25 final evidence package")


def _verify_artifact_registry(
    rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        role = row["role"]
        if role not in EXPECTED_REVIEW_STATUS_BY_ROLE or role in result:
            raise ValueError("V25 final artifact registry role coverage drifted")
        source = Path(row["path"]).resolve()
        review = Path(row["review_path"]).resolve()
        source_seal = verify_complete_seal(
            source, row["root_sha256"], label=f"V25 final {role} source"
        )
        review_seal = verify_complete_seal(
            review,
            row["review_root_sha256"],
            label=f"V25 final {role} review",
        )
        if (source / "run.exit").read_bytes() != b"0\n" or (
            review / "run.exit"
        ).read_bytes() != b"0\n":
            raise ValueError(f"V25 final {role} source/review did not exit successfully")
        review_report = _canonical_json(review / "report.json")
        if (
            review_report.get("status") != EXPECTED_REVIEW_STATUS_BY_ROLE.get(role)
            or review_report.get("reviewed_root_sha256") != source_seal["root_sha256"]
            or (
                "fixed_dp_head" in review_report
                and review_report["fixed_dp_head"] != FIXED_DP_HEAD
            )
        ):
            raise ValueError(f"V25 final {role} independent-review binding drifted")
        result[role] = {
            "source": source,
            "review": review,
            "source_root_sha256": source_seal["root_sha256"],
            "review_root_sha256": review_seal["root_sha256"],
            "review_report": review_report,
        }
    if set(result) != set(REQUIRED_ARTIFACT_ROLES):
        raise ValueError("V25 final required artifact roles are incomplete")
    return result


def _load_scientific_payloads(
    artifacts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    atom = Path(artifacts["train_only_atom_audit"]["source"])
    training = Path(artifacts["main_training"]["source"])
    auxiliary = Path(artifacts["auxiliary_static14d_full"]["source"])
    calibration = Path(artifacts["calibration_freeze"]["source"])
    preopen = Path(artifacts["fresh_b2_preopen"]["source"])
    evaluation = Path(artifacts["fresh_b2_evaluation"]["source"])
    calibration_payload = validate_calibration_freeze_payload(
        _canonical_json(calibration / "calibration_freeze.json")
    )
    preopen_payload = _canonical_json(preopen / "preopen_qualification.json")
    if set(preopen_payload) != {
        "schema_version",
        "status",
        "preopen_inputs_sha256",
        "frozen_root_bindings",
        "calibration_contract_root_sha256",
        "qualification",
        "qualification_rows",
        "fresh_b2_opened",
        "outcome_fields_consumed",
    }:
        raise ValueError("V25 final preopen payload field set drifted")
    qualification = validate_fresh_b2_preopen_qualification(
        preopen_payload["qualification"]
    )
    return {
        "atom_audit": _canonical_json(atom / "atom_audit.json"),
        "training_report": _canonical_json(training / "report.json"),
        "training_model_reports": _canonical_json(training / "model_reports.json"),
        "auxiliary_report": _canonical_json(auxiliary / "report.json"),
        "calibration_contract": calibration_payload["calibration_contract"],
        "preopen_qualification": qualification,
        "benchmark_b_evaluation": _canonical_json(evaluation / "evaluation.json"),
    }


def _canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = _strict_json_value(raw)
    if type(value) is not dict or raw != _canonical_bytes(value):
        raise ValueError(f"V25 final authority JSON is not canonical: {path}")
    return value


def _strict_json_object(path: Path) -> dict[str, Any]:
    value = _strict_json_value(path.read_bytes())
    if type(value) is not dict:
        raise ValueError(f"V25 frozen config is not an object: {path}")
    return value


def _strict_json_value(raw: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("V25 final JSON contains a duplicate key")
            result[key] = value
        return result

    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"V25 final JSON contains nonfinite token {token}")
        ),
    )


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()


def _tracked_dirty(root: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=root,
            text=True,
        ).strip()
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    root = build_final_evidence_artifact(
        input_manifest=args.input_manifest,
        output_dir=args.output_dir,
    )
    print(json.dumps({"status": "sealed", "root_sha256": root}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
