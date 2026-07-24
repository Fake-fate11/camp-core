#!/usr/bin/env python3
"""Independently review a sealed generic holdout success or fatal execution."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
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
from camp_core.integrations.diffusion_planner_v25_fresh_execution_review import (  # noqa: E402
    review_holdout_three_arm_execution,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (  # noqa: E402
    _strict_canonical_json,
    validate_fatal_artifact,
)
from camp_core.integrations.diffusion_planner_v25_holdout_opening_rc import (  # noqa: E402
    validate_production_rc_controller_decision,
    validate_production_rc_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_holdout_state import (  # noqa: E402
    validate_operational_attempt,
    validate_scientific_ledger,
)
from camp_core.integrations.diffusion_planner_v25_holdout_preopen_dispatch import (  # noqa: E402
    holdout_preopen_files,
    validate_holdout_preopen_authority,
)
from camp_core.integrations.diffusion_planner_v25_holdout_plan_dispatch import (  # noqa: E402
    NONFRESH_CANARY_SPLIT,
    validate_holdout_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    load_v25_runtime_selector_assets,
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = "camp_dp_v25_holdout_execution_review_artifact_v1"
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
    execution_artifact: Path,
    execution_root_sha256: str,
    controller_decision_artifact: Path,
    controller_decision_root_sha256: str,
    opening_release_artifact: Path,
    opening_release_root_sha256: str,
    probe_template: Path,
    probe_template_sha256: str,
    dp_repo: Path,
    output_dir: Path,
) -> str:
    execution = Path(execution_artifact).resolve()
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
    verify_complete_seal(
        execution, execution_root_sha256, label="holdout execution"
    )
    release_root = Path(opening_release_artifact).resolve()
    controller_root = Path(controller_decision_artifact).resolve()
    verify_complete_seal(
        release_root,
        opening_release_root_sha256,
        label="holdout opening release",
    )
    verify_complete_seal(
        controller_root,
        controller_decision_root_sha256,
        label="holdout controller decision",
    )
    if (
        (release_root / "run.exit").read_bytes() != b"0\n"
        or (controller_root / "run.exit").read_bytes() != b"0\n"
    ):
        raise ValueError("holdout reviewed controller/release did not pass")
    release = validate_production_rc_opening_release(
        _canonical_json(release_root / "decision.json")
    )
    controller = validate_production_rc_controller_decision(
        _canonical_json(controller_root / "decision.json")
    )
    if (
        release["controller_decision_root_sha256"]
        != controller_decision_root_sha256
        or controller["holdout_identity"] != release["holdout_identity"]
        or controller["experiment_protocol"] != release["experiment_protocol"]
    ):
        raise ValueError("holdout reviewed controller/release drifted")
    operational = validate_operational_attempt(
        _strict_canonical_json(Path(release["operational_attempt_path"]))
    )
    scientific_path = Path(release["scientific_ledger_path"])
    scientific = (
        validate_scientific_ledger(
            _strict_canonical_json(scientific_path)
        )
        if scientific_path.exists()
        else None
    )
    run_exit = (execution / "run.exit").read_bytes()
    if run_exit == b"1\n":
        fatal = validate_fatal_artifact(
            _canonical_json(execution / "fatal.json")
        )
        if (
            (
                scientific is not None
                and (
                    scientific["state"] != "terminal_failure"
                    or scientific["terminal_artifact_root_sha256"]
                    != execution_root_sha256
                )
            )
            or (
                scientific is None
                and operational["state"] != "pre_exposure_failure"
            )
            or fatal["opening_release_root_sha256"]
            != opening_release_root_sha256
            or fatal["holdout_identity_sha256"]
            != release["holdout_identity"]["holdout_identity_sha256"]
            or fatal["experiment_protocol_sha256"]
            != release["experiment_protocol"][
                "experiment_protocol_sha256"
            ]
        ):
            raise ValueError("holdout fatal execution/tombstone drifted")
        result = {
            "schema_version": SCHEMA_VERSION,
            "status": "passed_independent_holdout_artifact_fatal_review",
            "reviewed_root_sha256": execution_root_sha256,
            "opening_release_root_sha256": opening_release_root_sha256,
            "holdout_identity_sha256": fatal["holdout_identity_sha256"],
            "planned_arm_run_count": fatal["planned_arm_run_count"],
            "attempted_arm_run_count": fatal["attempted_arm_run_count"],
            "complete_arm_run_count": fatal["complete_arm_run_count"],
            "unattempted_arm_run_count": fatal[
                "unattempted_arm_run_count"
            ],
            "full_denominator_formed": False,
            "fresh_outcome_evaluated": False,
            "claim_authorized_by_review": False,
        }
    elif run_exit == b"0\n":
        if (
            scientific is None
            or scientific["state"] != "full_denominator_formed"
            or scientific["terminal_artifact_root_sha256"] is not None
        ):
            raise ValueError("holdout success execution/tombstone drifted")
        preopen_root = Path(release["preopen_authority"]["path"]).resolve()
        verify_complete_seal(
            preopen_root,
            release["preopen_authority"]["root_sha256"],
            label="holdout reviewed preopen",
        )
        if (preopen_root / "run.exit").read_bytes() != b"0\n":
            raise ValueError("holdout reviewed preopen did not pass")
        preopen = validate_holdout_preopen_authority(
            _canonical_json(preopen_root / "preopen_authority.json")
        )
        _verify_execution_upstream_authorities_independent(
            preopen=preopen,
            split=preopen["holdout_identity"]["split"],
        )
        preopen_files = holdout_preopen_files(
            preopen["holdout_identity"]["split"]
        )
        plan = validate_holdout_execution_plan(
            _canonical_json(preopen_root / preopen_files["plan"])
        )
        prepared_rows = _canonical_value(
            preopen_root / preopen_files["prepared_runtime"]
        )
        prepared = {
            row["scenario_identity_sha256"]: row for row in prepared_rows
        }
        route_manifest = _canonical_json(
            preopen_root / preopen_files["route_assets"]
        )
        route_by_identity = {
            row["route_identity_sha256"]: row["route_asset"]
            for row in route_manifest["route_assets"]
        }
        bindings = preopen["upstream_bindings"]
        training = Path(bindings["training"]["path"]).resolve()
        training_review = Path(bindings["training_review"]["path"]).resolve()
        assets = load_v25_runtime_selector_assets(
            training_artifact=training,
            training_root_sha256=bindings["training"]["root_sha256"],
            training_review_artifact=training_review,
            training_review_root_sha256=bindings["training_review"][
                "root_sha256"
            ],
        )
        selector = _independent_runtime_selector_authority(
            assets=assets,
            training=training,
            training_review=training_review,
            bindings=bindings,
            release=release,
        )
        artifact_report = _canonical_json(
            execution / "artifact_report.json"
        )
        consumption = artifact_report["opening_consumption"]
        independent = review_holdout_three_arm_execution(
            artifact=execution,
            plan=plan,
            qualification_rows=preopen["runtime_qualification_rows"],
            probe_template=_legacy_json_object(
                Path(probe_template).resolve(), probe_template_sha256
            ),
            prepared_runtime_by_scenario=prepared,
            route_asset_by_identity=route_by_identity,
            dp_repo=Path(dp_repo).resolve(),
            runtime_selector_authority=selector,
            opening_release=release,
            opening_release_root_sha256=opening_release_root_sha256,
            opening_consumption=consumption,
        )
        result = {
            "schema_version": SCHEMA_VERSION,
            "status": "passed_independent_holdout_execution_review",
            "reviewed_root_sha256": execution_root_sha256,
            "opening_release_root_sha256": opening_release_root_sha256,
            "holdout_identity_sha256": release["holdout_identity"][
                "holdout_identity_sha256"
            ],
            "experiment_protocol_sha256": release[
                "experiment_protocol"
            ]["experiment_protocol_sha256"],
            "independent_execution_review": independent,
            "full_denominator_formed": True,
            "fresh_outcome_evaluated": False,
            "claim_authorized_by_review": False,
        }
    else:
        raise ValueError("holdout execution run.exit drifted")
    output.mkdir(parents=True)
    _write_json(output / "report.json", result)
    (output / "HEADS").write_bytes(
        (
            f"camp_head={release['pointer_head_at_release']}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (output / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(output, label="independent V25 holdout execution review")


def _verify_execution_upstream_authorities_independent(
    *, preopen: Mapping[str, Any], split: str
) -> None:
    if split == "fresh_b4":
        _verify_upstream_role_contract_independent(
            preopen["upstream_authority_role_contract"],
            bindings=preopen["upstream_bindings"],
        )
        return
    if split != NONFRESH_CANARY_SPLIT:
        raise ValueError(f"unsupported reviewed holdout split: {split}")
    upstream_bindings = preopen["upstream_bindings"]
    fixture_bindings = preopen["source_fixture_bindings"]
    if (
        type(upstream_bindings) is not dict
        or type(fixture_bindings) is not dict
        or set(upstream_bindings) & set(fixture_bindings)
    ):
        raise ValueError("independent nonFresh all-success bindings drifted")
    sealed_bindings = dict(upstream_bindings)
    sealed_bindings.update(fixture_bindings)
    for role, raw_binding in sealed_bindings.items():
        binding = _independent_binding(raw_binding, role)
        upstream = Path(binding["path"])
        verify_complete_seal(
            upstream,
            binding["root_sha256"],
            label=f"reviewed holdout upstream {role}",
        )
        if (upstream / "run.exit").read_bytes() != b"0\n":
            raise ValueError(f"reviewed holdout upstream failed: {role}")


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
        != hashlib.sha256(_canonical_bytes(unsigned)).hexdigest()
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
            raise ValueError(f"independent upstream terminal drifted: {role}")
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
                disposition,
                bindings=bindings,
                payloads=payloads,
            )
        elif mode == "accepted_via_closeout":
            _verify_closeout_disposition_independent(
                role,
                disposition,
                bindings=bindings,
                payloads=payloads,
            )
        else:
            raise ValueError(
                f"independent unknown authority disposition: {role}"
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
        _canonical_bytes(chain)
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
        "holdout_identity_sha256": disposition["holdout_identity_sha256"],
    }
    if is_b3:
        failure_review = _independent_binding(
            disposition["embedded_failure_review"],
            f"{role} failure review",
        )
        chain["embedded_failure_review"] = failure_review
    if disposition["chain_id_sha256"] != hashlib.sha256(
        _canonical_bytes(chain)
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
    failure_payload = _canonical_json(failure_path / failure_file)
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
        review_payload = _canonical_json(review_path / "report.json")
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
        or any(char not in "0123456789abcdef" for char in value["root_sha256"])
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


def _independent_authority_object(
    path: Path, *, byte_policy: str
) -> dict[str, Any]:
    raw = path.read_bytes()
    value = _strict_parse_json(raw, path)
    if type(value) is not dict:
        raise ValueError(f"independent authority object required: {path}")
    if byte_policy == "camp_canonical":
        if raw != _canonical_bytes(value):
            raise ValueError(
                f"independent authority JSON is not canonical: {path}"
            )
    elif byte_policy != "strict_sealed_legacy":
        raise ValueError(
            f"independent authority JSON byte policy drifted: {path}"
        )
    return value


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-artifact", type=Path, required=True)
    parser.add_argument("--execution-root-sha256", required=True)
    parser.add_argument("--controller-decision-artifact", type=Path, required=True)
    parser.add_argument("--controller-decision-root-sha256", required=True)
    parser.add_argument("--opening-release-artifact", type=Path, required=True)
    parser.add_argument("--opening-release-root-sha256", required=True)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--probe-template-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    root = review(**vars(_arguments()))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))
    return 0


def _independent_runtime_selector_authority(
    *,
    assets: Any,
    training: Path,
    training_review: Path,
    bindings: Mapping[str, Mapping[str, str]],
    release: Mapping[str, Any],
) -> dict[str, Any]:
    protocol = release["experiment_protocol"]
    authority = {
        "training_artifact": dict(bindings["training"]),
        "training_review_artifact": dict(bindings["training_review"]),
        "calibration_contract_root_sha256": bindings[
            "calibration_freeze"
        ]["root_sha256"],
        "preopen_qualification_root_sha256": release[
            "preopen_authority"
        ]["root_sha256"],
        "scenario_manifest_root_sha256": release["holdout_identity"][
            "scenario_manifest_sha256"
        ],
        "model_registry_sha256": _file_sha256(
            training / "model_registry.json"
        ),
        "training_scale_sha256": assets.atom_scales_sha256,
        "context_scaler_sha256": (
            assets.scene14d_weight_provider.context_scaler_sha256
        ),
        "atom_scales": {
            "path": str(training / "runtime_atom_scales.json"),
            "sha256": assets.atom_scales_sha256,
        },
        "static14d_weights": {
            "path": str(training / "static14d_runtime_weights.npy"),
            "sha256": assets.static14d_weights_sha256,
        },
    }
    if any(
        authority[name] != protocol[name]
        for name in (
            "model_registry_sha256",
            "training_scale_sha256",
            "context_scaler_sha256",
        )
    ):
        raise ValueError("reviewed holdout runtime assets differ from protocol")
    return authority


def _canonical_json(path: Path) -> dict[str, Any]:
    value = _canonical_value(path)
    if type(value) is not dict:
        raise ValueError(f"reviewed holdout JSON is not an object: {path}")
    return value


def _canonical_value(path: Path) -> Any:
    raw = Path(path).read_bytes()
    value = _strict_parse_json(raw, path)
    if raw != _canonical_bytes(value):
        raise ValueError(f"reviewed holdout JSON is not canonical: {path}")
    return value


def _legacy_json_object(path: Path, expected_sha256: str) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    if _file_sha256(path) != expected_sha256:
        raise ValueError("reviewed holdout probe template SHA256 drifted")
    value = _strict_parse_json(raw, path)
    if type(value) is not dict:
        raise ValueError("reviewed holdout probe template is not an object")
    return value


def _strict_parse_json(raw: bytes, path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    return json.loads(
        raw.decode("utf-8", "strict"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {path}: {token}")
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


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
