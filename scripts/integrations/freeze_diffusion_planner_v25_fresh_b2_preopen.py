#!/usr/bin/env python3
"""Materialize the single outcome-blind V25 Fresh-B2 pre-open authority."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
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
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (  # noqa: E402
    FIXED_DP_HEAD,
    build_preopen_authority,
    canonical_json_bytes,
    verify_bound_artifact,
)
from camp_core.integrations.diffusion_planner_v25_atom_mechanism import (  # noqa: E402
    BINDING_SCHEMA_VERSION as ATOM_MECHANISM_BINDING_SCHEMA_VERSION,
    mechanism_names,
    validate_atom_mechanism_binding,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (  # noqa: E402
    build_signal_complete_suite,
    validate_signal_complete_suite,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (  # noqa: E402
    build_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (  # noqa: E402
    build_signal_complete_runtime_case,
)


SCHEMA_VERSION = "camp_dp_v25_fresh_b2_preopen_materialization_v1"
CONFIG_SCHEMA_VERSION = "camp_dp_v25_fresh_b2_preopen_authority_config_v1"
UPSTREAM_REPORT_ROLES = frozenset(
    {
        "corrected_corpus",
        "corrected_corpus_review",
        "training",
        "training_review",
        "calibration_recovery",
        "calibration_recovery_review",
    }
)


def build(
    *,
    config_path: Path,
    storage_artifact: Path,
    storage_root_sha256: str,
    storage_review_artifact: Path,
    storage_review_root_sha256: str,
    atom_mechanism_artifact: Path,
    atom_mechanism_root_sha256: str,
    atom_mechanism_review_artifact: Path,
    atom_mechanism_review_root_sha256: str,
    output_dir: Path,
) -> str:
    if _tracked_dirty():
        raise ValueError("CAMP tracked worktree must be clean")
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    config = _validate_config(_canonical_json(config_path))
    implementation_head = _git_head(ROOT)
    upstream = _open_upstream(config)
    storage = _open_storage(
        storage_artifact=storage_artifact,
        storage_root_sha256=storage_root_sha256,
        storage_review_artifact=storage_review_artifact,
        storage_review_root_sha256=storage_review_root_sha256,
    )
    atom_mechanism = _open_atom_mechanism(
        artifact=atom_mechanism_artifact,
        root_sha256=atom_mechanism_root_sha256,
        review_artifact=atom_mechanism_review_artifact,
        review_root_sha256=atom_mechanism_review_root_sha256,
    )
    suite = build_signal_complete_suite("fresh_b2")
    plan = build_signal_complete_execution_plan("fresh_b2")
    output.mkdir(parents=True)
    try:
        maps_root = output / "maps"
        maps_root.mkdir()
        for relative, payload in suite["map_payloads"].items():
            path = maps_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        suite_receipt = validate_signal_complete_suite(suite)
        prepared = [
            build_signal_complete_runtime_case(
                identity,
                map_artifact=maps_root,
                seeds=plan["seeds"],
            )
            for identity in plan["identities"]
        ]
        authority = build_preopen_authority(
            repo_root=ROOT,
            implementation_head=implementation_head,
            upstream_bindings=upstream["bindings"],
            train_source_rows=upstream["train_source_rows"],
            calibration_preregistration=upstream["preregistration"],
            calibration_preregistration_sha256=upstream["preregistration_sha256"],
            calibration_analysis=upstream["calibration_analysis"],
            suite_receipt=suite,
            map_artifact=maps_root,
            license_sha256=_sha256(ROOT / "LICENSE"),
            prepared_runtime_cases=prepared,
            storage_manifest=storage["manifest"],
            storage_review_status=storage["review_status"],
            atom_mechanism_binding=atom_mechanism,
            free_bytes_before=shutil.disk_usage(output.parent).free,
            output_parent=output.parent,
        )
        _write_json(output / "fresh_b2_map_suite.json", suite_receipt)
        _write_json(output / "fresh_b2_execution_plan.json", plan)
        _write_json(output / "fresh_b2_prepared_runtime_cases.json", prepared)
        _write_json(output / "accepted_evaluation_preregistration.json", upstream["preregistration"])
        _write_json(output / "preopen_authority.json", authority)
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": "passed_outcome_blind_fresh_b2_preopen_materialization",
            "camp_head": implementation_head,
            "fixed_dp_head": FIXED_DP_HEAD,
            "config_path": str(config_path.resolve()),
            "config_sha256": _sha256(config_path),
            "upstream_bindings": upstream["bindings"],
            "storage_artifact": {
                "path": str(storage_artifact.resolve()),
                "root_sha256": storage_root_sha256,
            },
            "storage_review_artifact": {
                "path": str(storage_review_artifact.resolve()),
                "root_sha256": storage_review_root_sha256,
            },
            "atom_mechanism_artifact": {
                "path": str(atom_mechanism_artifact.resolve()),
                "root_sha256": atom_mechanism_root_sha256,
            },
            "atom_mechanism_review_artifact": {
                "path": str(atom_mechanism_review_artifact.resolve()),
                "root_sha256": atom_mechanism_review_root_sha256,
            },
            "preopen_authority_sha256": _sha256(output / "preopen_authority.json"),
            "map_suite_sha256": _sha256(output / "fresh_b2_map_suite.json"),
            "execution_plan_sha256": _sha256(output / "fresh_b2_execution_plan.json"),
            "prepared_runtime_cases_sha256": _sha256(output / "fresh_b2_prepared_runtime_cases.json"),
            "accepted_evaluation_preregistration_sha256": _sha256(
                output / "accepted_evaluation_preregistration.json"
            ),
            "map_count": 25,
            "route_count": 100,
            "paired_unit_count": 500,
            "arm_run_count": 1500,
            "tick_capacity": 96_000,
            "preopen_model_loaded": False,
            "preopen_dp_forward_executed": False,
            "fresh_open_authorized": False,
            "nonce_created": False,
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
        }
        _write_json(output / "report.json", report)
        (output / "HEADS").write_bytes(
            f"camp_head={implementation_head}\nfixed_dp_head={FIXED_DP_HEAD}\n".encode("ascii")
        )
        (output / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode())
        (output / "run.exit").write_bytes(b"0\n")
        return seal_artifact(output, label="V25 Fresh B2 consolidated pre-open authority")
    except BaseException as exc:
        _write_json(
            output / "failure.json",
            {
                "schema_version": SCHEMA_VERSION,
                "status": "failed_closed_outcome_blind_fresh_b2_preopen_materialization",
                "reason": str(exc),
                "fresh_b2_opened": False,
                "outcome_fields_consumed": [],
            },
        )
        (output / "run.exit").write_bytes(b"1\n")
        seal_artifact(output, label="failed V25 Fresh B2 pre-open authority")
        raise


def _open_upstream(config: Mapping[str, Any]) -> dict[str, Any]:
    bindings: dict[str, dict[str, str]] = {}
    reports: dict[str, dict[str, Any]] = {}
    for role, item in config["upstream_artifacts"].items():
        path = Path(item["path"])
        verify_bound_artifact(path, item["root_sha256"], exit_code=item["run_exit"])
        bindings[role] = {"path": str(path), "root_sha256": item["root_sha256"]}
        if role in UPSTREAM_REPORT_ROLES:
            reports[role] = _canonical_json(path / "report.json")
    if (
        reports["training"].get("status") != "passed_strict_convex_training"
        or reports["training_review"].get("status")
        != "passed_independent_strict_convex_training_review"
        or reports["training_review"].get("reviewed_root_sha256")
        != bindings["training"]["root_sha256"]
        or reports["calibration_recovery"].get("status")
        != "recovered_calibration_analysis_complete_fresh_closed"
        or reports["calibration_recovery"].get("original_execution_root_sha256")
        != bindings["calibration_raw"]["root_sha256"]
        or reports["calibration_recovery_review"].get("status")
        != "passed_independent_paired_calibration_recovery_review"
        or reports["calibration_recovery_review"].get(
            "reviewed_recovery_root_sha256"
        )
        != bindings["calibration_recovery"]["root_sha256"]
    ):
        raise ValueError("Fresh B2 accepted training/calibration chain drifted")

    corpus_report = reports["corrected_corpus"]
    source_path = Path(str(corpus_report["r0_source_artifact"])).resolve()
    source_root = str(corpus_report["r0_source_root_sha256"])
    verify_complete_seal(source_path, source_root, label="Fresh B2 train route-source authority")
    source_payload = _canonical_json(source_path / "route_signal_source_receipts.json")
    if source_payload.get("source_failures") != [] or len(source_payload.get("cases", [])) != 1653:
        raise ValueError("Fresh B2 train route-source denominator drifted")
    bindings["train_route_source"] = {"path": str(source_path), "root_sha256": source_root}

    input_roots = reports["calibration_recovery"].get("input_roots")
    if type(input_roots) is not dict:
        raise ValueError("Fresh B2 recovery input roots are missing")
    prereg_path = Path(str(input_roots["preregistration_artifact"])).resolve()
    prereg_root = str(input_roots["preregistration_root_sha256"])
    prereg_review_path = Path(str(input_roots["preregistration_review_artifact"])).resolve()
    prereg_review_root = str(input_roots["preregistration_review_root_sha256"])
    verify_bound_artifact(prereg_path, prereg_root, exit_code=0)
    verify_bound_artifact(prereg_review_path, prereg_review_root, exit_code=0)
    prereg_review = _canonical_json(prereg_review_path / "report.json")
    if prereg_review.get("reviewed_root_sha256") != prereg_root:
        raise ValueError("Fresh B2 accepted preregistration review drifted")
    bindings["calibration_preregistration"] = {"path": str(prereg_path), "root_sha256": prereg_root}
    bindings["calibration_preregistration_review"] = {
        "path": str(prereg_review_path),
        "root_sha256": prereg_review_root,
    }
    preregistration = _canonical_json(prereg_path / "preregistration.json")
    return {
        "bindings": bindings,
        "train_source_rows": source_payload["cases"],
        "preregistration": preregistration,
        "preregistration_sha256": _sha256(prereg_path / "preregistration.json"),
        "calibration_analysis": _canonical_json(
            Path(bindings["calibration_recovery"]["path"]) / "calibration_analysis.json"
        ),
    }


def _open_storage(
    *,
    storage_artifact: Path,
    storage_root_sha256: str,
    storage_review_artifact: Path,
    storage_review_root_sha256: str,
) -> dict[str, Any]:
    verify_bound_artifact(storage_artifact, storage_root_sha256, exit_code=0)
    verify_bound_artifact(storage_review_artifact, storage_review_root_sha256, exit_code=0)
    review = _canonical_json(storage_review_artifact / "report.json")
    if (
        review.get("status")
        != "passed_independent_fresh_storage_equivalence_and_capacity_review"
        or review.get("reviewed_root_sha256") != storage_root_sha256
    ):
        raise ValueError("Fresh B2 storage review binding drifted")
    return {
        "manifest": _canonical_json(storage_artifact / "storage_manifest.json"),
        "review_status": review["status"],
    }


def _open_atom_mechanism(
    *,
    artifact: Path,
    root_sha256: str,
    review_artifact: Path,
    review_root_sha256: str,
) -> dict[str, Any]:
    verify_bound_artifact(artifact, root_sha256, exit_code=0)
    verify_bound_artifact(review_artifact, review_root_sha256, exit_code=0)
    report = _canonical_json(artifact / "report.json")
    review = _canonical_json(review_artifact / "report.json")
    if (
        report.get("status") != "frozen_atom_mechanism_ready_before_fresh_b2_opening"
        or report.get("fresh_storage_capacity_gate_passed") is not True
        or report.get("raw_k8_payload_copied") is not False
        or report.get("primary_fresh_design_changed") is not False
        or report.get("model_or_weight_changed") is not False
        or report.get("single_atom_closed_loop_causal_effect_claimed") is not False
        or report.get("fresh_b2_opened") is not False
        or report.get("fresh_outcome_fields_consumed") != []
        or review.get("status") != "passed_independent_atom_mechanism_preopen_review"
        or review.get("reviewed_root_sha256") != root_sha256
        or review.get("fresh_storage_capacity_gate_passed") is not True
        or review.get("fresh_b2_opened") is not False
        or review.get("fresh_outcome_fields_consumed") != []
    ):
        raise ValueError("Fresh B2 atom-mechanism authority drifted")
    return validate_atom_mechanism_binding(
        {
            "schema_version": ATOM_MECHANISM_BINDING_SCHEMA_VERSION,
            "status": "passed_independent_atom_mechanism_preopen_review",
            "artifact_path": str(artifact.resolve()),
            "artifact_root_sha256": root_sha256,
            "review_artifact_path": str(review_artifact.resolve()),
            "review_root_sha256": review_root_sha256,
            "contract_sha256": report["contract_sha256"],
            "analysis_sha256": report["calibration_atom_mechanism_sha256"],
            "decision_tick_count": report["decision_tick_count"],
            "mechanism_names": mechanism_names(),
            "raw_k8_payload_copied": False,
            "primary_fresh_design_changed": False,
            "model_or_weight_changed": False,
            "single_atom_closed_loop_causal_effect_claimed": False,
            "fresh_storage_capacity_gate_passed": True,
            "storage_projected_1500_arm_upper_bound_nbytes_with_mechanism": report[
                "storage_projected_1500_arm_upper_bound_nbytes_with_mechanism"
            ],
            "fresh_b2_opened": False,
            "fresh_outcome_fields_consumed": [],
        }
    )


def _validate_config(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or value.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise ValueError("Fresh B2 pre-open config schema drifted")
    if (
        value.get("status") != "frozen_outcome_blind_preopen_materialization"
        or value.get("fixed_dp_head") != FIXED_DP_HEAD
        or value.get("one_time_state", {}).get("nonce_created") is not False
        or value.get("one_time_state", {}).get("fresh_b2_opened") is not False
        or value.get("one_time_state", {}).get("outcome_fields_consumed") != []
    ):
        raise ValueError("Fresh B2 pre-open config closed-state drifted")
    artifacts = value.get("upstream_artifacts")
    if type(artifacts) is not dict or set(artifacts) != {
        "corrected_corpus",
        "corrected_corpus_review",
        "training",
        "training_review",
        "calibration_raw",
        "calibration_recovery",
        "calibration_recovery_review",
    }:
        raise ValueError("Fresh B2 pre-open upstream role set drifted")
    for role, item in artifacts.items():
        if type(item) is not dict or set(item) != {"path", "root_sha256", "run_exit"}:
            raise ValueError(f"Fresh B2 pre-open {role} binding drifted")
        path = Path(str(item["path"]))
        if not path.is_absolute() or str(path.resolve()) != str(path):
            raise ValueError(f"Fresh B2 pre-open {role} path is not canonical")
        if type(item["root_sha256"]) is not str or len(item["root_sha256"]) != 64:
            raise ValueError(f"Fresh B2 pre-open {role} root is invalid")
        if type(item["run_exit"]) is not int or item["run_exit"] not in {0, 1}:
            raise ValueError(f"Fresh B2 pre-open {role} exit is invalid")
    return json.loads(json.dumps(value))


def _canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_no_duplicate_pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )
    if type(value) is not dict or raw != canonical_json_bytes(value):
        raise ValueError(f"authority JSON is not canonical: {path}")
    return value


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes(value))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head(path: Path) -> str:
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def _tracked_dirty() -> bool:
    return bool(
        subprocess.check_output(
            ["git", "-C", str(ROOT), "status", "--short", "--untracked-files=no"],
            text=True,
        ).strip()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--storage-artifact", type=Path, required=True)
    parser.add_argument("--storage-root-sha256", required=True)
    parser.add_argument("--storage-review-artifact", type=Path, required=True)
    parser.add_argument("--storage-review-root-sha256", required=True)
    parser.add_argument("--atom-mechanism-artifact", type=Path, required=True)
    parser.add_argument("--atom-mechanism-root-sha256", required=True)
    parser.add_argument("--atom-mechanism-review-artifact", type=Path, required=True)
    parser.add_argument("--atom-mechanism-review-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = build(
        config_path=args.config,
        storage_artifact=args.storage_artifact,
        storage_root_sha256=args.storage_root_sha256,
        storage_review_artifact=args.storage_review_artifact,
        storage_review_root_sha256=args.storage_review_root_sha256,
        atom_mechanism_artifact=args.atom_mechanism_artifact,
        atom_mechanism_root_sha256=args.atom_mechanism_root_sha256,
        atom_mechanism_review_artifact=args.atom_mechanism_review_artifact,
        atom_mechanism_review_root_sha256=args.atom_mechanism_review_root_sha256,
        output_dir=args.output_dir,
    )
    print(json.dumps({"status": "sealed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
