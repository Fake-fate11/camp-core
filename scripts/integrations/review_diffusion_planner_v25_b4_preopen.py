#!/usr/bin/env python3
"""Independently rebuild and review the sealed Fresh B4 pre-open authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_b3_preopen import (
    validate_b3_preopen_authority,
)
from camp_core.integrations.diffusion_planner_v25_b4_preopen import (
    FIXED_DP_HEAD,
    build_b4_preopen_authority,
    validate_b4_preopen_authority,
)
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (
    canonical_json_bytes,
    tracked_implementation_manifest,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
    strict_equal,
)
from camp_core.integrations.diffusion_planner_v25_holdout_state import (
    operational_identity_path,
    scientific_identity_path,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (
    build_signal_complete_suite,
    validate_signal_complete_suite,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (
    build_signal_complete_runtime_case,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_routes import (
    validate_signal_complete_route_assets,
)
from scripts.integrations.materialize_diffusion_planner_v25_signal_complete_routes import (
    _route_class,
)


SCHEMA_VERSION = "camp_dp_v25_fresh_b4_preopen_independent_review_v2"
CAS_ROOT = Path("/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas")
ROLE_CONTRACT_SCHEMA_VERSION = (
    "camp_dp_v25_upstream_authority_role_contract_v1"
)


_ROLE_ROWS = (
    ("accepted_b3_preopen", "preopen_authority.json", "camp_dp_v25_fresh_b3_consolidated_preopen_authority_v1", "passed_outcome_blind_fresh_b3_preopen_authority", 0, "direct_success", "accepted_b3_preopen_review"),
    ("accepted_b3_preopen_review", "report.json", "camp_dp_v25_fresh_b3_preopen_independent_review_v1", "passed_independent_fresh_b3_preopen_review", 0, "direct_success", None),
    ("atom_mechanism", "report.json", "camp_dp_v25_atom_mechanism_artifact_v1", "frozen_atom_mechanism_ready_before_fresh_b2_opening", 0, "direct_success", "atom_mechanism_review"),
    ("atom_mechanism_review", "report.json", "camp_dp_v25_atom_mechanism_review_v1", "passed_independent_atom_mechanism_preopen_review", 0, "direct_success", None),
    ("b2_consumed_failure", "closeout.json", "camp_dp_v25_consumed_holdout_failure_closeout_v1", "terminal_consumed_one_shot_engineering_failure", 0, "accepted_via_closeout", "b2_consumed_failure_review"),
    ("b2_consumed_failure_review", "report.json", "camp_dp_v25_consumed_holdout_failure_review_v1", "passed_independent_consumed_holdout_failure_review", 0, "direct_success", None),
    ("b3_terminal_closeout", "closeout.json", "camp_dp_v25_holdout_terminal_failure_closeout_v1", "consumed_one_shot_engineering_failure_no_evaluation_no_claim", 0, "accepted_via_closeout", "b3_terminal_closeout_review"),
    ("b3_terminal_closeout_review", "report.json", "camp_dp_v25_holdout_terminal_failure_closeout_review_v1", "passed_independent_holdout_terminal_failure_closeout_review", 0, "direct_success", None),
    ("calibration_freeze", "report.json", "camp_dp_v25_calibration_freeze_from_paired_artifact_v1", "calibration_freeze_passed", 0, "direct_success", "calibration_freeze_review"),
    ("calibration_freeze_review", "report.json", "camp_dp_v25_calibration_freeze_from_paired_review_v1", "passed_independent_calibration_freeze_from_paired_review", 0, "direct_success", None),
    ("calibration_preregistration", "report.json", "camp_dp_v25_paired_calibration_preregistration_artifact_v1", "paired_calibration_preregistration_frozen", 0, "direct_success", "calibration_preregistration_review"),
    ("calibration_preregistration_review", "report.json", "camp_dp_v25_paired_calibration_preregistration_review_v1", "passed_independent_paired_calibration_preregistration_review", 0, "direct_success", None),
    ("calibration_raw", "failure.json", "camp_dp_v25_paired_calibration_execution_artifact_v1", "failed_closed_paired_calibration_execution", 1, "accepted_via_recovery", None),
    ("calibration_recovery", "report.json", "camp_dp_v25_paired_calibration_recovery_analysis_v1", "recovered_calibration_analysis_complete_fresh_closed", 0, "direct_success", "calibration_recovery_review"),
    ("calibration_recovery_review", "report.json", "camp_dp_v25_paired_calibration_recovery_review_v1", "passed_independent_paired_calibration_recovery_review", 0, "direct_success", None),
    ("corrected_corpus", "report.json", "camp_dp_v25_controlled_training_corpus_execution_v8", "passed", 0, "direct_success", "corrected_corpus_review"),
    ("corrected_corpus_review", "report.json", "camp_dp_v25_controlled_training_corpus_review_v8", "passed_independent_full_corpus_review", 0, "direct_success", None),
    ("production_equivalence_certificate", "preflight.json", "camp_dp_v25_nonfresh_production_equivalence_certificate_v3", "passed_nonfresh_production_equivalence_certificate", 0, "direct_success", "production_equivalence_certificate_review"),
    ("production_equivalence_certificate_review", "report.json", "camp_dp_v25_nonfresh_production_equivalence_certificate_independent_review_v2", "passed_independent_nonfresh_production_equivalence_review", 0, "direct_success", None),
    ("storage", "report.json", "camp_dp_v25_fresh_storage_qualification_artifact_v1", "passed_fresh_storage_equivalence_and_capacity", 0, "direct_success", "storage_review"),
    ("storage_review", "report.json", "camp_dp_v25_fresh_storage_qualification_review_v1", "passed_independent_fresh_storage_equivalence_and_capacity_review", 0, "direct_success", None),
    ("train_route_source", "report.json", "camp_dp_v25_a161_route_signal_source_census_v2", "passed_source_only_route_signal_authority_census", 0, "direct_success", None),
    ("training", "report.json", "camp_dp_v25_strict_convex_training_artifact_v1", "passed_strict_convex_training", 0, "direct_success", "training_review"),
    ("training_review", "report.json", "camp_dp_v25_strict_convex_training_review_v1", "passed_independent_strict_convex_training_review", 0, "direct_success", None),
)
_ROLE_ORACLE = {
    row[0]: {
        "payload_file": row[1],
        "schema_version": row[2],
        "status": row[3],
        "run_exit": row[4],
        "mode": row[5],
        "review_role": row[6],
        "json_byte_policy": (
            "strict_sealed_legacy"
            if row[0] in {"corrected_corpus", "corrected_corpus_review"}
            else "camp_canonical"
        ),
    }
    for row in _ROLE_ROWS
}


def review(
    *,
    source_artifact: Path,
    source_root_sha256: str,
    output_dir: Path,
) -> str:
    source = source_artifact.resolve()
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    seal = verify_complete_seal(
        source, source_root_sha256, label="Fresh B4 pre-open"
    )
    if (source / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh B4 pre-open did not pass")
    paths = set(seal["manifest_paths"])
    fixed = {
        "COMMAND",
        "HEADS",
        "fresh_b4_execution_plan.json",
        "fresh_b4_map_suite.json",
        "fresh_b4_prepared_runtime_cases.json",
        "fresh_b4_route_assets.json",
        "preopen_authority.json",
        "report.json",
        "run.exit",
    }
    maps = {path for path in paths if path.startswith("maps/")}
    route_files = {
        path for path in paths if path.startswith("route_materialization/")
    }
    if paths != fixed | maps | route_files or len(maps) != 25:
        raise ValueError("Fresh B4 pre-open inventory drifted")
    stored = validate_b4_preopen_authority(
        _canonical_object(source / "preopen_authority.json")
    )
    suite_full = build_signal_complete_suite("fresh_b4")
    suite_receipt = validate_signal_complete_suite(suite_full)
    if not strict_equal(
        _canonical_object(source / "fresh_b4_map_suite.json"),
        suite_receipt,
    ):
        raise ValueError("Fresh B4 map suite receipt drifted")
    for relative, payload in suite_full["map_payloads"].items():
        path = source / "maps" / relative
        if not path.is_file() or path.is_symlink() or path.read_bytes() != payload:
            raise ValueError(f"Fresh B4 map payload drifted: {relative}")
    plan = build_signal_complete_execution_plan("fresh_b4")
    if not strict_equal(
        _canonical_object(source / "fresh_b4_execution_plan.json"), plan
    ):
        raise ValueError("Fresh B4 execution plan drifted")
    route_class, _route_source = _route_class(
        Path("/root/autodl-tmp/Diffusion-Planner")
    )
    route_manifest = validate_signal_complete_route_assets(
        _canonical_object(source / "fresh_b4_route_assets.json"),
        plan=plan,
        map_artifact=source / "maps",
        route_class=route_class,
    )
    if (
        not route_files
        or not strict_equal(
            _canonical_object(
                source / "route_materialization" / "route_assets.json"
            ),
            route_manifest,
        )
        or not strict_equal(stored["route_assets"], route_manifest)
    ):
        raise ValueError("Fresh B4 route materialization drifted")
    prepared = [
        build_signal_complete_runtime_case(
            identity,
            map_artifact=source / "maps",
            seeds=plan["seeds"],
        )
        for identity in plan["identities"]
    ]
    if not strict_equal(
        _canonical_value(source / "fresh_b4_prepared_runtime_cases.json"),
        prepared,
    ):
        raise ValueError("Fresh B4 prepared runtime cases drifted")

    bindings = stored["upstream_bindings"]
    _verify_upstream_role_contract_independent(
        stored["upstream_authority_role_contract"],
        bindings=bindings,
    )
    train_source = _strict_external_object(
        Path(bindings["train_route_source"]["path"])
        / "route_signal_source_receipts.json"
    )
    if train_source.get("source_failures") != []:
        raise ValueError("Fresh B4 train source failures drifted")
    prior = validate_b3_preopen_authority(
        _canonical_object(
            Path(bindings["accepted_b3_preopen"]["path"])
            / "preopen_authority.json"
        )
    )
    b2_closeout = _canonical_object(
        Path(bindings["b2_consumed_failure"]["path"]) / "closeout.json"
    )
    b2_review = _canonical_object(
        Path(bindings["b2_consumed_failure_review"]["path"]) / "report.json"
    )
    b3_closeout = _canonical_object(
        Path(bindings["b3_terminal_closeout"]["path"]) / "closeout.json"
    )
    b3_review = _canonical_object(
        Path(bindings["b3_terminal_closeout_review"]["path"]) / "report.json"
    )
    certificate = _canonical_object(
        Path(bindings["production_equivalence_certificate"]["path"])
        / "preflight.json"
    )
    certificate_review = _canonical_object(
        Path(bindings["production_equivalence_certificate_review"]["path"])
        / "report.json"
    )
    storage = _canonical_object(
        Path(bindings["storage"]["path"]) / "storage_manifest.json"
    )
    identity_sha = stored["holdout_identity"]["holdout_identity_sha256"]
    operational_exists = operational_identity_path(
        CAS_ROOT, identity_sha
    ).exists()
    scientific_exists = scientific_identity_path(CAS_ROOT, identity_sha).exists()
    expected = build_b4_preopen_authority(
        implementation_head=_git_head(),
        critical_implementation_manifest=tracked_implementation_manifest(ROOT),
        upstream_bindings=bindings,
        upstream_authority_role_contract=stored[
            "upstream_authority_role_contract"
        ],
        train_source_rows=train_source["cases"],
        calibration_plan=build_signal_complete_execution_plan("calibration"),
        b2_plan=build_signal_complete_execution_plan("fresh_b2"),
        b3_plan=build_signal_complete_execution_plan("fresh_b3"),
        b4_suite=suite_full,
        b4_plan=plan,
        b4_map_artifact=source / "maps",
        route_asset_manifest=route_manifest,
        license_sha256=_sha256(ROOT / "LICENSE"),
        prepared_runtime_cases=prepared,
        prior_experiment_protocol=prior["experiment_protocol"],
        b2_consumed_failure=b2_closeout,
        b2_consumed_failure_review=b2_review,
        b3_terminal_closeout=b3_closeout,
        b3_terminal_closeout_review=b3_review,
        production_equivalence_certificate=certificate,
        production_equivalence_certificate_review=certificate_review,
        power=prior["power"],
        evaluation=prior["evaluation"],
        storage_manifest=storage,
        atom_mechanism_binding=bindings["atom_mechanism"],
        atom_mechanism_review_binding=bindings["atom_mechanism_review"],
        free_bytes_before=stored["capacity"]["free_bytes_before"],
        output_parent=Path(stored["capacity"]["canonical_output_parent"]),
        operational_attempt_exists=operational_exists,
        scientific_ledger_exists=scientific_exists,
    )
    if not strict_equal(stored, expected):
        raise ValueError("Fresh B4 pre-open differs from independent rebuild")
    report = _canonical_object(source / "report.json")
    if (
        report.get("status")
        != "passed_outcome_blind_fresh_b4_preopen_materialization"
        or report.get("camp_head") != _git_head()
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("holdout_identity_sha256") != identity_sha
        or report.get("prior_holdout_raw_values_used") is not False
        or report.get("operational_attempt_exists") is not False
        or report.get("scientific_ledger_exists") is not False
        or report.get("fresh_b4_opened") is not False
        or report.get("outcome_fields_consumed") != []
    ):
        raise ValueError("Fresh B4 pre-open report drifted")
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_fresh_b4_preopen_review",
        "reviewed_root_sha256": source_root_sha256,
        "implementation_head": _git_head(),
        "fixed_dp_head": FIXED_DP_HEAD,
        "holdout_identity_sha256": identity_sha,
        "experiment_protocol_sha256": stored["experiment_protocol"][
            "experiment_protocol_sha256"
        ],
        "critical_implementation_manifest_sha256": stored[
            "critical_implementation_manifest"
        ]["manifest_sha256"],
        "actual_native_receipt_contract_sha256": stored[
            "actual_native_receipt_contract"
        ]["contract_sha256"],
        "upstream_authority_role_contract_sha256": stored[
            "upstream_authority_role_contract"
        ]["contract_sha256"],
        "map_count": 25,
        "route_count": 100,
        "paired_unit_count": 500,
        "arm_run_count": 1500,
        "tick_capacity": 96_000,
        "train_cal_b1_b2_b3_b4_zero_overlap": True,
        "prior_holdout_raw_values_used": False,
        "production_equivalence_certificate_reviewed": True,
        "operational_attempt_exists": False,
        "scientific_ledger_exists": False,
        "storage_capacity_passed": True,
        "fresh_open_authorized": False,
        "nonce_created": False,
        "fresh_b4_opened": False,
        "outcome_fields_consumed": [],
    }
    output.mkdir(parents=True)
    (output / "report.json").write_bytes(canonical_json_bytes(result))
    (output / "HEADS").write_bytes(
        (
            f"camp_head={result['implementation_head']}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (output / "COMMAND").write_bytes(
        (" ".join(sys.argv) + "\n").encode("utf-8")
    )
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(
        output, label="independent V25 Fresh B4 consolidated pre-open review"
    )


def _verify_upstream_role_contract_independent(
    contract: Any,
    *,
    bindings: Any,
) -> None:
    if type(bindings) is not dict or set(bindings) != set(_ROLE_ORACLE):
        raise ValueError("independent upstream role binding set drifted")
    if type(contract) is not dict or set(contract) != {
        "schema_version",
        "status",
        "role_count",
        "roles",
        "contract_sha256",
    }:
        raise ValueError("independent upstream role contract fields drifted")
    if (
        contract["schema_version"] != ROLE_CONTRACT_SCHEMA_VERSION
        or contract["status"]
        != "frozen_complete_upstream_authority_role_contract"
        or type(contract["role_count"]) is not int
        or contract["role_count"] != len(_ROLE_ORACLE)
        or type(contract["roles"]) is not list
        or len(contract["roles"]) != len(_ROLE_ORACLE)
    ):
        raise ValueError("independent upstream role contract header drifted")
    unsigned = dict(contract)
    claimed_sha = unsigned.pop("contract_sha256")
    if (
        type(claimed_sha) is not str
        or claimed_sha
        != hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest()
    ):
        raise ValueError("independent upstream role contract SHA drifted")
    rows: dict[str, dict[str, Any]] = {}
    payloads: dict[str, dict[str, Any]] = {}
    for row in contract["roles"]:
        if type(row) is not dict or set(row) != {
            "role",
            "binding",
            "execution_terminal",
            "authority_disposition",
        }:
            raise ValueError("independent upstream role row fields drifted")
        role = row["role"]
        if (
            type(role) is not str
            or role not in _ROLE_ORACLE
            or role in rows
        ):
            raise ValueError("independent unknown or duplicate upstream role")
        spec = _ROLE_ORACLE[role]
        binding = _independent_binding(bindings[role], role)
        if not _literal_equal(row["binding"], binding):
            raise ValueError(f"independent upstream binding drifted: {role}")
        terminal = {
            "run_exit": spec["run_exit"],
            "payload_file": spec["payload_file"],
            "schema_version": spec["schema_version"],
            "status": spec["status"],
            "json_byte_policy": spec["json_byte_policy"],
        }
        if not _literal_equal(row["execution_terminal"], terminal):
            raise ValueError(
                f"independent upstream terminal drifted: {role}"
            )
        path = Path(binding["path"])
        verify_complete_seal(
            path, binding["root_sha256"], label=f"review upstream {role}"
        )
        if (path / "run.exit").read_bytes() != (
            f"{spec['run_exit']}\n".encode("ascii")
        ):
            raise ValueError(
                f"independent native-int run.exit drifted: {role}"
            )
        payload = _independent_authority_object(
            path / spec["payload_file"],
            byte_policy=spec["json_byte_policy"],
        )
        if (
            payload.get("schema_version") != spec["schema_version"]
            or payload.get("status") != spec["status"]
        ):
            raise ValueError(f"independent upstream payload drifted: {role}")
        rows[role] = row
        payloads[role] = payload
    if set(rows) != set(_ROLE_ORACLE):
        raise ValueError("independent upstream role set incomplete")
    for role, spec in _ROLE_ORACLE.items():
        disposition = rows[role]["authority_disposition"]
        mode = spec["mode"]
        if type(disposition) is not dict or disposition.get("mode") != mode:
            raise ValueError(
                f"independent authority disposition drifted: {role}"
            )
        if mode == "direct_success":
            if disposition != {
                "mode": mode,
                "independent_review_role": spec["review_role"],
            }:
                raise ValueError(
                    f"independent direct-success disposition drifted: {role}"
                )
            if spec["review_role"] is not None:
                review = payloads[spec["review_role"]]
                root_field = (
                    "reviewed_recovery_root_sha256"
                    if role == "calibration_recovery"
                    else "reviewed_root_sha256"
                )
                path_field = (
                    "reviewed_recovery_artifact"
                    if role == "calibration_recovery"
                    else "reviewed_artifact"
                )
                if (
                    review.get(root_field) != bindings[role]["root_sha256"]
                    or review.get(path_field)
                    not in {None, bindings[role]["path"]}
                ):
                    raise ValueError(
                        f"independent review crosslink drifted: {role}"
                    )
        elif mode == "accepted_via_recovery":
            _verify_recovery_disposition_independent(
                disposition, bindings=bindings, payloads=payloads
            )
        else:
            _verify_closeout_disposition_independent(
                role,
                disposition,
                bindings=bindings,
                payloads=payloads,
            )


def _verify_recovery_disposition_independent(
    disposition: Mapping[str, Any],
    *,
    bindings: Mapping[str, Mapping[str, str]],
    payloads: Mapping[str, Mapping[str, Any]],
) -> None:
    if set(disposition) != {
        "mode",
        "recovery_role",
        "recovery_review_role",
        "chain_id_sha256",
    } or (
        disposition["recovery_role"] != "calibration_recovery"
        or disposition["recovery_review_role"]
        != "calibration_recovery_review"
    ):
        raise ValueError("independent calibration recovery disposition drifted")
    chain = {
        "raw": bindings["calibration_raw"],
        "recovery": bindings["calibration_recovery"],
        "recovery_review": bindings["calibration_recovery_review"],
    }
    if disposition["chain_id_sha256"] != hashlib.sha256(
        canonical_json_bytes(chain)
    ).hexdigest():
        raise ValueError("independent calibration recovery chain SHA drifted")
    raw = bindings["calibration_raw"]
    recovery = payloads["calibration_recovery"]
    review = payloads["calibration_recovery_review"]
    if (
        recovery.get("original_execution_artifact") != raw["path"]
        or recovery.get("original_execution_root_sha256")
        != raw["root_sha256"]
        or type(recovery.get("original_execution_run_exit")) is not int
        or recovery.get("original_execution_run_exit") != 1
        or review.get("original_execution_artifact") != raw["path"]
        or review.get("original_execution_root_sha256")
        != raw["root_sha256"]
        or type(review.get("original_execution_run_exit")) is not int
        or review.get("original_execution_run_exit") != 1
        or review.get("reviewed_recovery_artifact")
        != bindings["calibration_recovery"]["path"]
        or review.get("reviewed_recovery_root_sha256")
        != bindings["calibration_recovery"]["root_sha256"]
    ):
        raise ValueError("independent calibration recovery crosslink drifted")


def _verify_closeout_disposition_independent(
    role: str,
    disposition: Mapping[str, Any],
    *,
    bindings: Mapping[str, Mapping[str, str]],
    payloads: Mapping[str, Mapping[str, Any]],
) -> None:
    is_b3 = role == "b3_terminal_closeout"
    expected_fields = {
        "mode",
        "independent_review_role",
        "embedded_failure",
        "holdout_identity_sha256",
        "chain_id_sha256",
    }
    if is_b3:
        expected_fields.add("embedded_failure_review")
    spec = _ROLE_ORACLE[role]
    if (
        set(disposition) != expected_fields
        or disposition["independent_review_role"] != spec["review_role"]
        or type(disposition["holdout_identity_sha256"]) is not str
        or len(disposition["holdout_identity_sha256"]) != 64
    ):
        raise ValueError(f"independent closeout disposition drifted: {role}")
    failure = _independent_binding(
        disposition["embedded_failure"], f"{role} failure"
    )
    chain: dict[str, Any] = {
        "closeout": bindings[role],
        "closeout_review": bindings[spec["review_role"]],
        "embedded_failure": failure,
        "holdout_identity_sha256": disposition[
            "holdout_identity_sha256"
        ],
    }
    if is_b3:
        failure_review = _independent_binding(
            disposition["embedded_failure_review"],
            f"{role} failure review",
        )
        chain["embedded_failure_review"] = failure_review
    if disposition["chain_id_sha256"] != hashlib.sha256(
        canonical_json_bytes(chain)
    ).hexdigest():
        raise ValueError(f"independent closeout chain SHA drifted: {role}")
    failure_path = Path(failure["path"])
    verify_complete_seal(
        failure_path,
        failure["root_sha256"],
        label=f"review {role} embedded failure",
    )
    failure_file = "fatal.json" if is_b3 else "failure.json"
    failure_schema = (
        "camp_dp_v25_holdout_artifact_fatal_v1"
        if is_b3
        else "camp_dp_v25_fresh_b2_execution_artifact_v2"
    )
    failure_status = (
        "artifact_fatal" if is_b3 else "failed_closed_fresh_b2_execution"
    )
    if (failure_path / "run.exit").read_bytes() != b"1\n":
        raise ValueError(f"independent closeout failure exit drifted: {role}")
    failure_payload = _canonical_object(failure_path / failure_file)
    if (
        failure_payload.get("schema_version") != failure_schema
        or failure_payload.get("status") != failure_status
    ):
        raise ValueError(
            f"independent closeout failure terminal drifted: {role}"
        )
    closeout_review = payloads[spec["review_role"]]
    if (
        closeout_review.get("reviewed_root_sha256")
        != bindings[role]["root_sha256"]
        or closeout_review.get("holdout_identity_sha256")
        != disposition["holdout_identity_sha256"]
    ):
        raise ValueError(
            f"independent closeout review crosslink drifted: {role}"
        )
    if is_b3:
        review_path = Path(failure_review["path"])
        verify_complete_seal(
            review_path,
            failure_review["root_sha256"],
            label="review B3 embedded failure review",
        )
        if (review_path / "run.exit").read_bytes() != b"0\n":
            raise ValueError("independent B3 failure review exit drifted")
        review_payload = _canonical_object(review_path / "report.json")
        if (
            review_payload.get("schema_version")
            != "camp_dp_v25_holdout_execution_review_artifact_v1"
            or review_payload.get("status")
            != "passed_independent_holdout_artifact_fatal_review"
            or review_payload.get("reviewed_root_sha256")
            != failure["root_sha256"]
            or review_payload.get("holdout_identity_sha256")
            != disposition["holdout_identity_sha256"]
        ):
            raise ValueError("independent B3 failure review drifted")


def _independent_binding(value: Any, label: str) -> dict[str, str]:
    if type(value) is not dict or set(value) != {"path", "root_sha256"}:
        raise ValueError(f"independent binding fields drifted: {label}")
    path = Path(value["path"])
    if (
        type(value["path"]) is not str
        or not path.is_absolute()
        or str(path.resolve()) != value["path"]
        or type(value["root_sha256"]) is not str
        or len(value["root_sha256"]) != 64
    ):
        raise ValueError(f"independent binding invalid: {label}")
    return dict(value)


def _literal_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _literal_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _literal_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def _canonical_object(path: Path) -> dict[str, Any]:
    value = _canonical_value(path)
    if type(value) is not dict:
        raise ValueError(f"canonical object required: {path}")
    return value


def _independent_authority_object(
    path: Path, *, byte_policy: str
) -> dict[str, Any]:
    raw = path.read_bytes()
    value = _parse(raw, path)
    if type(value) is not dict:
        raise ValueError(f"independent authority object required: {path}")
    if byte_policy == "camp_canonical":
        if raw != canonical_json_bytes(value):
            raise ValueError(
                f"independent authority JSON is not canonical: {path}"
            )
    elif byte_policy != "strict_sealed_legacy":
        raise ValueError(
            f"independent authority JSON byte policy drifted: {path}"
        )
    return value


def _canonical_value(path: Path) -> Any:
    raw = path.read_bytes()
    value = _parse(raw, path)
    if raw != canonical_json_bytes(value):
        raise ValueError(f"authority JSON is not canonical: {path}")
    return value


def _strict_external_object(path: Path) -> dict[str, Any]:
    value = _parse(path.read_bytes(), path)
    if type(value) is not dict:
        raise ValueError(f"sealed external JSON object required: {path}")
    return value


def _parse(raw: bytes, path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    value = json.loads(
        raw.decode("utf-8", "strict"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {path}: {token}")
        ),
    )
    _require_finite_json(value, path=path)
    return value


def _require_finite_json(value: Any, *, path: Path) -> None:
    if type(value) is float and not math.isfinite(value):
        raise ValueError(f"nonfinite JSON value in {path}")
    if type(value) is list:
        for item in value:
            _require_finite_json(item, path=path)
    elif type(value) is dict:
        for item in value.values():
            _require_finite_json(item, path=path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-artifact", type=Path, required=True)
    parser.add_argument("--source-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = review(
        source_artifact=args.source_artifact,
        source_root_sha256=args.source_root_sha256,
        output_dir=args.output_dir,
    )
    print(root)


if __name__ == "__main__":
    main()
