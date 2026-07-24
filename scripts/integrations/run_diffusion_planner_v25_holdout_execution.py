#!/usr/bin/env python3
"""Consume one generic holdout CAS reservation and execute its sealed plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Mapping

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
from camp_core.integrations.diffusion_planner_v25_fresh_execution import (  # noqa: E402
    execute_holdout_three_arm_units,
    materialize_fixed_dp_failure_evidence,
)
from camp_core.integrations.diffusion_planner_v25_fresh_receipt import (  # noqa: E402
    project_candidate0_supplementary_native_receipt,
)
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (  # noqa: E402
    tracked_implementation_manifest,
)
from camp_core.integrations.diffusion_planner_v25_fresh_storage import (  # noqa: E402
    compress_logical_json_file,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (  # noqa: E402
    freeze_fatal_artifact,
)
from camp_core.integrations.diffusion_planner_v25_holdout_opening_rc import (  # noqa: E402
    freeze_scientific_exposure_receipt,
    validate_production_rc_controller_decision,
    validate_production_rc_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_holdout_state import (  # noqa: E402
    fail_operational_pre_exposure,
    mark_full_denominator,
    start_scientific_exposure,
    terminate_scientific_identity,
    validate_operational_attempt,
    validate_scientific_ledger,
)
from camp_core.integrations.diffusion_planner_v25_holdout_preopen_dispatch import (  # noqa: E402
    expected_holdout_preopen_review_status,
    holdout_preopen_files,
    validate_holdout_preopen_authority,
)
from camp_core.integrations.diffusion_planner_v25_holdout_plan_dispatch import (  # noqa: E402
    NONFRESH_CANARY_SPLIT,
    validate_holdout_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    V25RuntimeSelectorAssets,
    load_v25_runtime_selector_assets,
)
from scripts.integrations.run_diffusion_planner_v25_fresh_b2_execution import (  # noqa: E402
    FIXED_DP_HEAD,
    MINIMUM_FREE_BYTES,
    TRAIN_LOCK,
    _canonical_json,
    _exclusive_lock,
    _file_sha256,
    _git_head,
    _legacy_json_object,
    _preconditions,
    _strict_json_equal,
    _tracked_dirty,
    _write_control_files,
    _write_json,
)


SCHEMA_VERSION = "camp_dp_v25_holdout_execution_artifact_v1"
RunOne = Callable[[Mapping[str, Any], Path], Mapping[str, Any]]


def _run_impl(
    *,
    probe_template: Path,
    probe_template_sha256: str,
    controller_decision_artifact: Path,
    controller_decision_root_sha256: str,
    opening_release_artifact: Path,
    opening_release_root_sha256: str,
    dp_repo: Path,
    output_dir: Path,
    device: str,
    run_one: RunOne | None = None,
) -> str:
    if device != "cuda":
        raise ValueError("holdout production execution requires cuda")
    output = Path(output_dir)
    if str(output) != str(output.resolve()):
        raise ValueError("holdout output path must be canonical")
    output = output.resolve()
    dp_root = Path(dp_repo).resolve()
    _preconditions(dp_root, output)
    probe = _legacy_json_object(
        Path(probe_template).resolve(), probe_template_sha256
    )
    release_root = Path(opening_release_artifact).resolve()
    verify_complete_seal(
        release_root,
        opening_release_root_sha256,
        label="holdout opening release",
    )
    if (release_root / "run.exit").read_bytes() != b"0\n":
        raise ValueError("holdout opening release did not pass")
    release = validate_production_rc_opening_release(
        _canonical_json(release_root / "decision.json")
    )
    controller_root = Path(controller_decision_artifact).resolve()
    verify_complete_seal(
        controller_root,
        controller_decision_root_sha256,
        label="holdout controller decision",
    )
    if (controller_root / "run.exit").read_bytes() != b"0\n":
        raise ValueError("holdout controller decision did not pass")
    controller = validate_production_rc_controller_decision(
        _canonical_json(controller_root / "decision.json")
    )
    if (
        controller_decision_root_sha256
        != release["controller_decision_root_sha256"]
        or any(
            not _strict_json_equal(
                controller[name],
                release[name],
            )
            for name in (
                "implementation_source_head",
                "pointer_head_at_release",
                "fixed_dp_head",
                "critical_implementation_manifest_sha256",
                "preopen_authority",
                "preopen_review",
                "production_composition_preflight",
                "production_composition_preflight_review",
                "b2_tombstone",
                "b2_failure_review",
                "holdout_identity",
                "experiment_protocol",
                "run_nonce",
                "authorized_output_dir",
                "operational_attempt_path",
                "operational_identity_reservation_path",
                "scientific_ledger_path",
                "actual_native_receipt_contract_sha256",
            )
        )
        or str(output) != release["authorized_output_dir"]
        or _git_head(ROOT) != release["pointer_head_at_release"]
        or _tracked_dirty(ROOT)
        or release["fixed_dp_head"] != FIXED_DP_HEAD
    ):
        raise ValueError("holdout controller/release/live authority drifted")

    preopen_root = Path(release["preopen_authority"]["path"]).resolve()
    preopen_review_root = Path(release["preopen_review"]["path"]).resolve()
    verify_complete_seal(
        preopen_root,
        release["preopen_authority"]["root_sha256"],
        label="holdout preopen",
    )
    verify_complete_seal(
        preopen_review_root,
        release["preopen_review"]["root_sha256"],
        label="holdout preopen review",
    )
    if (
        (preopen_root / "run.exit").read_bytes() != b"0\n"
        or (preopen_review_root / "run.exit").read_bytes() != b"0\n"
    ):
        raise ValueError("holdout preopen authority chain did not pass")
    preopen = validate_holdout_preopen_authority(
        _canonical_json(preopen_root / "preopen_authority.json")
    )
    split = preopen["holdout_identity"]["split"]
    preopen_files = holdout_preopen_files(split)
    preopen_review = _canonical_json(preopen_review_root / "report.json")
    manifest = tracked_implementation_manifest(ROOT)
    if (
        preopen_review.get("status")
        != expected_holdout_preopen_review_status(split)
        or preopen_review.get("reviewed_root_sha256")
        != release["preopen_authority"]["root_sha256"]
        or preopen["holdout_identity"] != release["holdout_identity"]
        or preopen["experiment_protocol"] != release["experiment_protocol"]
        or preopen["critical_implementation_manifest"] != manifest
        or manifest["manifest_sha256"]
        != release["critical_implementation_manifest_sha256"]
    ):
        raise ValueError("holdout preopen/release authority drifted")
    if split in {"fresh_b4", NONFRESH_CANARY_SPLIT}:
        sealed_bindings = dict(preopen["upstream_bindings"])
        if split == NONFRESH_CANARY_SPLIT:
            sealed_bindings.update(preopen["source_fixture_bindings"])
        for upstream_role, upstream_binding in sealed_bindings.items():
            upstream_path = Path(upstream_binding["path"]).resolve()
            verify_complete_seal(
                upstream_path,
                upstream_binding["root_sha256"],
                label=f"{split} execution upstream {upstream_role}",
            )
            if (upstream_path / "run.exit").read_bytes() != b"0\n":
                raise ValueError(
                    f"{split} execution upstream did not pass: {upstream_role}"
                )
    for role in (
        "production_composition_preflight",
        "production_composition_preflight_review",
        "b2_tombstone",
        "b2_failure_review",
    ):
        binding = release[role]
        verify_complete_seal(
            Path(binding["path"]),
            binding["root_sha256"],
            label=f"holdout {role}",
        )
        if (Path(binding["path"]) / "run.exit").read_bytes() != b"0\n":
            raise ValueError(f"holdout {role} did not pass")

    plan = validate_holdout_execution_plan(
        _canonical_json(preopen_root / preopen_files["plan"])
    )
    prepared_rows = _canonical_value(
        preopen_root / preopen_files["prepared_runtime"]
    )
    if type(prepared_rows) is not list:
        raise ValueError("holdout prepared runtime inventory drifted")
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
    qualifications = preopen["runtime_qualification_rows"]
    bindings = preopen["upstream_bindings"]
    training = Path(bindings["training"]["path"]).resolve()
    training_review = Path(bindings["training_review"]["path"]).resolve()
    verify_complete_seal(
        training, bindings["training"]["root_sha256"], label="training"
    )
    verify_complete_seal(
        training_review,
        bindings["training_review"]["root_sha256"],
        label="training review",
    )
    _verify_runtime_asset_hashes(
        training=training,
        protocol=release["experiment_protocol"],
    )

    with _exclusive_lock(TRAIN_LOCK):
        exposure: dict[str, Any] = {}
        try:
            assets = load_v25_runtime_selector_assets(
                training_artifact=training,
                training_root_sha256=bindings["training"]["root_sha256"],
                training_review_artifact=training_review,
                training_review_root_sha256=bindings["training_review"][
                    "root_sha256"
                ],
            )
            selector_authority = _runtime_selector_authority(
                assets=assets,
                training=training,
                training_review=training_review,
                bindings=bindings,
                release=release,
            )
            def start_exposure() -> Mapping[str, Any]:
                if exposure:
                    raise FileExistsError(
                        "holdout exposure starter was invoked twice"
                    )
                operational, scientific = start_scientific_exposure(
                    Path(release["scientific_ledger_path"]).parent.parent,
                    operational_attempt=Path(
                        release["operational_attempt_path"]
                    ),
                    first_unit_ordinal=plan["execution_units"][0][
                        "unit_ordinal"
                    ],
                    first_arm=plan["execution_units"][0]["ordered_arms"][0],
                )
                receipt = freeze_scientific_exposure_receipt(
                    opening_release=release,
                    opening_release_root_sha256=(
                        opening_release_root_sha256
                    ),
                    operational_attempt=operational,
                    scientific_ledger=scientific,
                )
                exposure.update(receipt)
                return receipt

            production_run = run_one or _native_run_one(
                device=device,
                assets=assets,
                opening_authority_provider=lambda: {
                    "opening_release": release,
                    "opening_release_root_sha256": (
                        opening_release_root_sha256
                    ),
                    "opening_consumption": dict(exposure),
                },
            )
            report = execute_holdout_three_arm_units(
                plan=plan,
                qualification_rows=qualifications,
                probe_template=probe,
                prepared_runtime_by_scenario=prepared,
                route_asset_by_identity=route_by_identity,
                dp_repo=dp_root,
                runtime_selector_authority=selector_authority,
                opening_release=release,
                opening_release_root_sha256=opening_release_root_sha256,
                opening_consumption=None,
                authorized_output_dir=release["authorized_output_dir"],
                output_dir=output,
                run_one=production_run,
                failure_evidence=materialize_fixed_dp_failure_evidence,
                start_exposure=start_exposure,
            )
            if not exposure:
                raise ValueError(
                    "holdout execution completed without scientific exposure"
                )
            artifact_report = {
                "schema_version": SCHEMA_VERSION,
                "status": "sealed_holdout_execution",
                "controller_decision_root_sha256": (
                    controller_decision_root_sha256
                ),
                "opening_release_root_sha256": (
                    opening_release_root_sha256
                ),
                "holdout_identity_sha256": release["holdout_identity"][
                    "holdout_identity_sha256"
                ],
                "experiment_protocol_sha256": release[
                    "experiment_protocol"
                ]["experiment_protocol_sha256"],
                "opening_consumption": dict(exposure),
                "execution_report_sha256": _canonical_sha(report),
                "fresh_opened_once": True,
                "training_executed": False,
                "calibration_executed": False,
                "claim_authorized_by_artifact": False,
            }
            _write_json(output / "artifact_report.json", artifact_report)
            _write_control_files(output, exit_code=0)
            root = seal_artifact(output, label="V25 holdout execution")
            mark_full_denominator(
                Path(release["scientific_ledger_path"]),
                planned_arm_run_count=plan["planned_arm_run_count"],
                terminal_arm_run_count=plan["planned_arm_run_count"],
            )
            return root
        except BaseException as exc:
            output.mkdir(parents=True, exist_ok=True)
            attempted, complete, unit, arm = _partial_counts(output, plan)
            scientific_path = Path(release["scientific_ledger_path"])
            exposed = scientific_path.exists()
            marker_path = (
                str(scientific_path)
                if exposed
                else release["operational_attempt_path"]
            )
            marker_sha = _file_sha256(Path(marker_path))
            fatal = freeze_fatal_artifact(
                block_class="holdout_execution_artifact_fatal",
                reason=str(exc),
                controller_decision_root_sha256=(
                    controller_decision_root_sha256
                ),
                opening_release_root_sha256=opening_release_root_sha256,
                marker_path=marker_path,
                marker_sha256=marker_sha,
                holdout_identity_sha256=release["holdout_identity"][
                    "holdout_identity_sha256"
                ],
                experiment_protocol_sha256=release[
                    "experiment_protocol"
                ]["experiment_protocol_sha256"],
                attempted_unit_ordinal=unit,
                attempted_arm=arm,
                planned_arm_run_count=plan["planned_arm_run_count"],
                attempted_arm_run_count=attempted,
                complete_arm_run_count=complete,
                outcome_fields_consumed=[],
                fresh_opened_once=exposed,
            )
            _write_json(output / "fatal.json", fatal)
            _write_control_files(output, exit_code=1)
            root = seal_artifact(output, label="failed V25 holdout execution")
            if exposed:
                scientific = validate_scientific_ledger(
                    _canonical_json(scientific_path)
                )
                if scientific["state"] in {
                    "terminal_failure",
                    "terminal_success",
                }:
                    raise ValueError(
                        "holdout scientific identity was already terminal"
                    ) from exc
                terminate_scientific_identity(
                    scientific_path,
                    expected_state=scientific["state"],
                    success=False,
                    terminal_artifact_root_sha256=root,
                    terminal_reason="artifact_fatal",
                )
            else:
                fail_operational_pre_exposure(
                    Path(release["operational_attempt_path"]),
                    expected_state="release_sealed",
                    terminal_reason="execution_pre_exposure_fatal",
                )
            raise


def run(
    *,
    probe_template: Path,
    probe_template_sha256: str,
    controller_decision_artifact: Path,
    controller_decision_root_sha256: str,
    opening_release_artifact: Path,
    opening_release_root_sha256: str,
    dp_repo: Path,
    output_dir: Path,
    device: str,
    run_one: RunOne | None = None,
) -> str:
    """Run once and release only a verified pre-exposure operational attempt."""

    try:
        return _run_impl(
            probe_template=probe_template,
            probe_template_sha256=probe_template_sha256,
            controller_decision_artifact=controller_decision_artifact,
            controller_decision_root_sha256=controller_decision_root_sha256,
            opening_release_artifact=opening_release_artifact,
            opening_release_root_sha256=opening_release_root_sha256,
            dp_repo=dp_repo,
            output_dir=output_dir,
            device=device,
            run_one=run_one,
        )
    except BaseException:
        # Authority or path checks can fail before the inner execution try.
        # Only a strictly sealed release may identify an operational ledger,
        # and only an unexposed release_sealed attempt may be released.
        try:
            release_root = Path(opening_release_artifact).resolve()
            verify_complete_seal(
                release_root,
                opening_release_root_sha256,
                label="holdout opening release",
            )
            release = validate_production_rc_opening_release(
                _canonical_json(release_root / "decision.json")
            )
            attempt_path = Path(release["operational_attempt_path"])
            attempt = validate_operational_attempt(
                _canonical_json(attempt_path)
            )
            scientific_path = Path(release["scientific_ledger_path"])
            if (
                attempt["state"] == "release_sealed"
                and not scientific_path.exists()
            ):
                fail_operational_pre_exposure(
                    attempt_path,
                    expected_state="release_sealed",
                    terminal_reason="production_entry_pre_exposure_fatal",
                )
        except BaseException:
            # Never replace the original failure or infer authority from an
            # unsealed/corrupt release.  Any ambiguous state remains blocked.
            pass
        raise


def _native_run_one(
    *,
    device: str,
    assets: V25RuntimeSelectorAssets,
    opening_authority_provider: Callable[[], Mapping[str, Any]],
) -> RunOne:
    holder: dict[str, Any] = {}

    def execute(
        config: Mapping[str, Any], run_dir: Path
    ) -> Mapping[str, Any]:
        if "run_arm" not in holder:
            from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
                build_native_arm_runner,
            )

            holder["run_arm"] = build_native_arm_runner(
                config,
                device=device,
                holdout_opening_authority=dict(
                    opening_authority_provider()
                ),
            )
        plan_arm = config["protocol"]["holdout_plan_arm"]
        snapshots: list[dict[str, Any]] = []
        primary_tensor_root = run_dir / "candidate_tensor_preimages_primary"
        primary_tensor_sink = _candidate_tensor_preimage_sink(
            primary_tensor_root
        )
        receipt = dict(
            holder["run_arm"](
                route=config["routes"][0],
                arm=(
                    "dp"
                    if plan_arm == "candidate0_operational_default"
                    else "camp"
                ),
                config=config,
                output_dir=run_dir / "native",
                max_steps=64,
                fixed_k8_candidate0=(
                    plan_arm == "candidate0_operational_default"
                ),
                v25_weight_provider=(
                    assets.scene14d_weight_provider
                    if plan_arm == "camp_scene14d_no_v2i"
                    else None
                ),
                decision_sink=(
                    snapshots.append
                    if plan_arm != "candidate0_operational_default"
                    else None
                ),
                candidate_tensor_sink=primary_tensor_sink,
                actual_native_receipt_sink=lambda raw: _write_json(
                    run_dir / "actual_native_receipt_raw.json",
                    raw,
                ),
            )
        )
        expected_indices = _expected_decision_evidence_indices(config)
        if len(snapshots) != len(expected_indices) or (
            snapshots
            and [row["sidecar"]["tick_index"] for row in snapshots]
            != expected_indices
        ):
            raise ValueError("holdout decision-evidence denominator drifted")
        # Fail-safe evidence ordering: the actual native callback output is
        # persisted before any candidate0 supplementary projection or
        # scientific row construction.  A projection/schema failure therefore
        # seals the exact producer-side receipt instead of losing the only
        # preimage that can localize the contract mismatch.
        _write_json(run_dir / "actual_native_receipt_raw.json", receipt)
        _seal_candidate_tensor_preimages(
            primary_tensor_root,
            expected_tick_count=(
                0 if plan_arm == "candidate0_operational_default" else 64
            ),
        )
        if plan_arm == "candidate0_operational_default":
            diagnostic_dir = run_dir / "_candidate0_supplementary_native_raw"
            supplementary_tensor_root = (
                run_dir / "candidate_tensor_preimages_supplementary"
            )
            diagnostic = dict(
                holder["run_arm"](
                    route=config["routes"][0],
                    arm="dp",
                    config=config,
                    output_dir=diagnostic_dir,
                    max_steps=64,
                    fixed_k8_candidate0=True,
                    candidate0_supplementary_pool_diagnostic=True,
                    candidate_tensor_sink=_candidate_tensor_preimage_sink(
                        supplementary_tensor_root
                    ),
                    actual_native_receipt_sink=lambda raw: _write_json(
                        run_dir
                        / "candidate0_supplementary_actual_native_raw.json",
                        raw,
                    ),
                )
            )
            _write_json(
                run_dir
                / "candidate0_supplementary_actual_native_raw.json",
                diagnostic,
            )
            _seal_candidate_tensor_preimages(
                supplementary_tensor_root, expected_tick_count=64
            )
            receipt[
                "_candidate0_supplementary_native_receipt"
            ] = project_candidate0_supplementary_native_receipt(diagnostic)
        logical = run_dir / "decision_evidence.json"
        _write_json(logical, snapshots)
        receipt["fresh_decision_evidence_reference"] = (
            compress_logical_json_file(logical)
        )
        receipt["fresh_decision_evidence_count"] = len(snapshots)
        return receipt

    return execute


def _expected_decision_evidence_indices(
    config: Mapping[str, Any],
) -> list[int]:
    protocol = config.get("protocol")
    if type(protocol) is not dict:
        raise ValueError("holdout decision-evidence protocol drifted")
    if protocol.get("holdout_plan_arm") == "candidate0_operational_default":
        return []
    sample_every = protocol.get("sample_every_ticks", 5)
    if (
        type(sample_every) is not int
        or type(sample_every) is bool
        or sample_every <= 0
    ):
        raise ValueError("holdout decision sampling cadence drifted")
    return list(range(0, 64, sample_every))


def _candidate_tensor_preimage_sink(
    root: Path,
) -> Callable[[int, np.ndarray, Mapping[str, Any]], None]:
    def persist(
        tick_index: int,
        candidate_tensor: np.ndarray,
        metadata: Mapping[str, Any],
    ) -> None:
        if (
            type(tick_index) is not int
            or not 0 <= tick_index < 64
            or not isinstance(candidate_tensor, np.ndarray)
        ):
            raise ValueError("candidate tensor preimage callback drifted")
        array = np.ascontiguousarray(candidate_tensor)
        if array.dtype != np.float32 or array.shape != (8, 80, 4):
            raise ValueError("candidate tensor preimage dtype/shape drifted")
        raw = array.tobytes(order="C")
        digest = hashlib.sha256(raw).hexdigest()
        if (
            type(metadata) is not dict
            or metadata.get("candidate_tensor_sha256") != digest
        ):
            raise ValueError("candidate tensor preimage metadata drifted")
        root.mkdir(parents=True, exist_ok=True)
        binary = root / f"tick_{tick_index:02d}.float32.bin"
        receipt = root / f"tick_{tick_index:02d}.json"
        if binary.exists() or receipt.exists():
            raise FileExistsError("candidate tensor preimage tick exists")
        with binary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        _write_json(
            receipt,
            {
                "schema_version": (
                    "camp_dp_v25_candidate_tensor_preimage_v1"
                ),
                "tick_index": tick_index,
                "dtype": "<f4",
                "shape": [8, 80, 4],
                "nbytes": len(raw),
                "candidate_tensor_sha256": digest,
                "native_metadata": dict(metadata),
                "persisted_before_projection": True,
            },
        )

    return persist


def _seal_candidate_tensor_preimages(
    root: Path, *, expected_tick_count: int
) -> None:
    if expected_tick_count == 0:
        if root.exists():
            raise ValueError(
                "candidate0 primary unexpectedly produced online K8 preimages"
            )
        return
    rows = []
    for tick_index in range(expected_tick_count):
        receipt = _canonical_json(root / f"tick_{tick_index:02d}.json")
        binary = root / f"tick_{tick_index:02d}.float32.bin"
        raw = binary.read_bytes()
        if (
            receipt["tick_index"] != tick_index
            or receipt["dtype"] != "<f4"
            or receipt["shape"] != [8, 80, 4]
            or receipt["nbytes"] != 8 * 80 * 4 * 4
            or receipt["candidate_tensor_sha256"]
            != hashlib.sha256(raw).hexdigest()
            or len(raw) != receipt["nbytes"]
            or receipt["persisted_before_projection"] is not True
        ):
            raise ValueError("candidate tensor preimage receipt drifted")
        rows.append(
            {
                "tick_index": tick_index,
                "candidate_tensor_sha256": receipt[
                    "candidate_tensor_sha256"
                ],
                "binary_relative_path": binary.name,
                "receipt_relative_path": (
                    root / f"tick_{tick_index:02d}.json"
                ).name,
            }
        )
    _write_json(
        root / "manifest.json",
        {
            "schema_version": (
                "camp_dp_v25_candidate_tensor_preimage_manifest_v1"
            ),
            "status": "persisted_before_projection",
            "tick_count": expected_tick_count,
            "dtype": "<f4",
            "shape": [8, 80, 4],
            "rows": rows,
        },
    )


def _runtime_selector_authority(
    *,
    assets: V25RuntimeSelectorAssets,
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
        raise ValueError("holdout runtime assets differ from protocol")
    return authority


def _verify_runtime_asset_hashes(
    *, training: Path, protocol: Mapping[str, Any]
) -> None:
    expected = {
        "model_registry.json": protocol["model_registry_sha256"],
        "runtime_atom_scales.json": protocol["training_scale_sha256"],
    }
    for relative, sha256 in expected.items():
        if _file_sha256(training / relative) != sha256:
            raise ValueError(f"holdout runtime asset drifted: {relative}")


def _partial_counts(
    output: Path, plan: Mapping[str, Any]
) -> tuple[int, int, int | None, str | None]:
    terminals = sorted((output / "runs").glob("*/terminal.json")) if (
        output / "runs"
    ).is_dir() else []
    attempted = len(list((output / "runs").iterdir())) if (
        output / "runs"
    ).is_dir() else 0
    complete = 0
    for path in terminals:
        try:
            if _canonical_json(path).get("status") == "complete":
                complete += 1
        except Exception:
            pass
    if attempted:
        ordinal = min(
            attempted // 3,
            len(plan["execution_units"]) - 1,
        )
        arm_index = min((attempted - 1) % 3, 2)
        plan_arm = plan["execution_units"][ordinal]["ordered_arms"][arm_index]
        arm = {
            "candidate0_operational_default": "candidate0",
            "camp_static14d": "static14d",
            "camp_scene14d_no_v2i": "scene14d",
        }[plan_arm]
        return attempted, complete, ordinal, arm
    return 0, 0, None, None


def _canonical_value(path: Path) -> Any:
    raw = path.read_bytes()
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate holdout JSON key: {key}")
            result[key] = value
        return result

    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=object_pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite holdout JSON token: {token}")
        ),
    )
    expected = (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    if raw != expected:
        raise ValueError(f"noncanonical holdout JSON: {path}")
    return value


def _canonical_sha(value: Any) -> str:
    import hashlib

    return hashlib.sha256(
        (
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--probe-template-sha256", required=True)
    parser.add_argument("--controller-decision-artifact", type=Path, required=True)
    parser.add_argument("--controller-decision-root-sha256", required=True)
    parser.add_argument("--opening-release-artifact", type=Path, required=True)
    parser.add_argument("--opening-release-root-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cuda",), required=True)
    parser.add_argument("--holdout-one-time-open", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if not args.holdout_one_time_open:
        raise ValueError("holdout production entry requires one-time open")
    root = run(
        probe_template=args.probe_template,
        probe_template_sha256=args.probe_template_sha256,
        controller_decision_artifact=args.controller_decision_artifact,
        controller_decision_root_sha256=(
            args.controller_decision_root_sha256
        ),
        opening_release_artifact=args.opening_release_artifact,
        opening_release_root_sha256=args.opening_release_root_sha256,
        dp_repo=args.dp_repo,
        output_dir=args.output_dir,
        device=args.device,
    )
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
