#!/usr/bin/env python3
"""Independently review the sealed V25 three-arm paired calibration."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from typing import Any, Mapping

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
from camp_core.integrations.diffusion_planner_causal_atoms import (  # noqa: E402
    FixedDpCandidateGenerationCapabilityFailure,
    validate_fixed_k8_candidate_tensor,
)
from camp_core.integrations.diffusion_planner_v25_calibration_analysis import (  # noqa: E402
    analyze_paired_calibration_outcomes,
)
from camp_core.integrations.diffusion_planner_v25_calibration_atoms import (  # noqa: E402
    analyze_calibration_decision_evidence,
)
from camp_core.integrations.diffusion_planner_v25_calibration_preregistration import (  # noqa: E402
    ROOT_ROLES,
    validate_paired_calibration_preregistration,
)
from camp_core.integrations.diffusion_planner_v25_paired_calibration import (  # noqa: E402
    ARMS,
    validate_paired_calibration_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_paired_calibration_execution import (  # noqa: E402
    CORPUS_SCHEMA_VERSION,
    FAILURE_SCHEMA_VERSION,
    RUN_RESULT_SCHEMA_VERSION,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    load_v25_runtime_selector_assets,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_execution import (  # noqa: E402
    build_paired_calibration_arm_config,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (  # noqa: E402
    validate_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (  # noqa: E402
    build_signal_complete_runtime_case,
)
from scripts.integrations.review_diffusion_planner_v25_candidate0_calibration import (  # noqa: E402
    _bind_reviewed_runtime_receipts,
    _canonical_json,
    _canonical_json_list,
    _canonical_sha,
    _canonical_value,
    _git_head,
    _legacy_json_object,
    _sha256,
    _strict_equal,
    _tracked_dirty,
    _write_json,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    validate_native_arm_receipt,
)


SCHEMA_VERSION = "camp_dp_v25_paired_calibration_execution_review_v1"
EXECUTION_SCHEMA_VERSION = "camp_dp_v25_paired_calibration_execution_artifact_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
ROOT_ROLES_CONSUMED = (
    "plan",
    "map",
    "route",
    "route_review",
    "runtime",
    "runtime_review",
    "paired_plan",
    "paired_plan_review",
    "preregistration",
    "preregistration_review",
    "training",
    "training_review",
)


def review(
    *,
    artifact: Path,
    artifact_root_sha256: str,
    dp_repo: Path,
    output_dir: Path,
) -> str:
    execution = artifact.resolve()
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    seal = verify_complete_seal(
        execution,
        artifact_root_sha256,
        label="paired calibration execution",
    )
    if (execution / "run.exit").read_bytes() != b"0\n":
        raise ValueError("paired calibration execution did not exit successfully")
    dp_root = dp_repo.resolve()
    if _git_head(dp_root) != FIXED_DP_HEAD or _tracked_dirty(dp_root):
        raise ValueError("fixed DP HEAD drifted or tracked worktree is dirty")

    report = _canonical_json(execution / "report.json")
    _validate_report(report, execution=execution)
    _validate_heads(execution / "HEADS", report)
    roots = report["input_roots"]
    _verify_input_roots(roots)

    base = validate_signal_complete_execution_plan(
        _canonical_json(Path(roots["plan_artifact"]) / "execution_plan.json")
    )
    paired = validate_paired_calibration_execution_plan(
        _canonical_json(
            Path(roots["paired_plan_artifact"]) / "paired_calibration_plan.json"
        ),
        calibration_plan=base,
    )
    preregistration = validate_paired_calibration_preregistration(
        _canonical_json(
            Path(roots["preregistration_artifact"]) / "preregistration.json"
        )
    )
    _verify_preregistered_root_chain(preregistration, roots)
    probe = _legacy_json_object(
        Path(report["probe_template"]), report["probe_template_sha256"]
    )

    map_root = Path(roots["map_artifact"])
    route_manifest = _canonical_json(
        Path(roots["route_artifact"]) / "route_assets.json"
    )
    route_rows = route_manifest.get("route_assets")
    if type(route_rows) is not list:
        raise ValueError("paired calibration route inventory is malformed")
    route_by_identity = {
        row["route_identity_sha256"]: dict(row["route_asset"])
        for row in route_rows
    }
    identities = {
        row["scenario_identity_sha256"]: row for row in paired["identities"]
    }
    prepared = {
        identity["scenario_identity_sha256"]: build_signal_complete_runtime_case(
            identity,
            map_artifact=map_root,
            seeds=base["seeds"],
        )
        for identity in base["identities"]
    }
    runtime_bindings = _bind_reviewed_runtime_receipts(
        plan=base,
        prepared_runtime_by_scenario=prepared,
        runtime_artifact=Path(roots["runtime_artifact"]),
    )
    if not _strict_equal(
        report["runtime_receipt_sha256_by_scenario"], runtime_bindings
    ):
        raise ValueError("paired calibration runtime receipt binding drifted")

    assets = load_v25_runtime_selector_assets(
        training_artifact=Path(roots["training_artifact"]),
        training_root_sha256=roots["training_root_sha256"],
        training_review_artifact=Path(roots["training_review_artifact"]),
        training_review_root_sha256=roots["training_review_root_sha256"],
    )
    selector_authority = _selector_authority(assets, roots)
    if not _strict_equal(report["runtime_selector_authority"], selector_authority):
        raise ValueError("paired calibration selector authority drifted")
    _verify_model_preregistration(preregistration, selector_authority, assets)

    results = _canonical_json_list(execution / "run_results.json")
    if len(results) != 300:
        raise ValueError("paired calibration terminal denominator drifted")
    run_dirs = sorted((execution / "runs").iterdir())
    if len(run_dirs) != 300 or any(not path.is_dir() for path in run_dirs):
        raise ValueError("paired calibration run directory denominator drifted")

    camp_runs: list[dict[str, Any]] = []
    results_by_pair: dict[int, dict[str, Mapping[str, Any]]] = defaultdict(dict)
    ordinal = 0
    for unit in paired["execution_units"]:
        identity = identities[unit["scenario_identity_sha256"]]
        route_asset = route_by_identity[identity["route_identity_sha256"]]
        for arm_order_index, plan_arm in enumerate(unit["ordered_arms"]):
            result = results[ordinal]
            run_dir = run_dirs[ordinal]
            expected_name = (
                f"{ordinal:04d}_{unit['unit_ordinal']:04d}_"
                f"{arm_order_index}_{plan_arm}"
            )
            if run_dir.name != expected_name:
                raise ValueError("paired calibration run directory order drifted")
            expected_config = build_paired_calibration_arm_config(
                probe_template=probe,
                prepared_runtime=prepared[unit["scenario_identity_sha256"]],
                execution_unit=unit,
                plan_arm=plan_arm,
                route_asset=route_asset,
                dp_repo=dp_root,
                runtime_selector_authority=selector_authority,
            )
            if not _strict_equal(
                _canonical_json(run_dir / "run_config.json"), expected_config
            ):
                raise ValueError("paired calibration run config drifted")
            terminal = _canonical_json(run_dir / "terminal.json")
            if not _strict_equal(terminal, result):
                raise ValueError("paired calibration terminal/result binding drifted")
            _review_terminal_metadata(
                result,
                ordinal=ordinal,
                unit=unit,
                identity=identity,
                arm_order_index=arm_order_index,
                plan_arm=plan_arm,
            )
            if result["status"] == "complete":
                decision = _review_complete(
                    execution=execution,
                    run_dir=run_dir,
                    result=result,
                    unit=unit,
                    identity=identity,
                    route_asset=route_asset,
                    plan_arm=plan_arm,
                )
                if decision is not None:
                    camp_runs.append(decision)
            elif result["status"] == "retained_fixed_dp_capability_failure":
                _review_failure(
                    execution,
                    run_dir=run_dir,
                    result=result,
                    unit=unit,
                    identity=identity,
                    plan_arm=plan_arm,
                )
            else:
                raise ValueError("paired calibration terminal status drifted")
            results_by_pair[unit["unit_ordinal"]][plan_arm] = result
            ordinal += 1

    _review_initial_pairing(results_by_pair)
    reconstructed = _independent_corpus(paired, results)
    recorded = _canonical_json(execution / "paired_calibration_corpus.json")
    if not _strict_equal(recorded, reconstructed):
        raise ValueError("paired calibration corpus differs from reconstruction")
    analysis = analyze_paired_calibration_outcomes(reconstructed)
    recorded_analysis = _canonical_json(execution / "calibration_analysis.json")
    if not _strict_equal(recorded_analysis, analysis):
        raise ValueError("paired calibration analysis differs from reconstruction")
    atom_calibration = analyze_calibration_decision_evidence(
        camp_runs=camp_runs,
        atom_scales=assets.atom_scales,
        static14d_weights=assets.static14d_weights,
        scene14d_provider=assets.scene14d_weight_provider,
        training_artifact=Path(roots["training_artifact"]),
    )
    recorded_atoms = _canonical_json(execution / "atom_calibration.json")
    if not _strict_equal(recorded_atoms, atom_calibration):
        raise ValueError("paired calibration atom evidence differs from reconstruction")
    _verify_report_accounting(
        report,
        results=results,
        corpus=recorded,
        analysis_path=execution / "calibration_analysis.json",
        atom_path=execution / "atom_calibration.json",
    )

    output.mkdir(parents=True)
    review_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_paired_calibration_execution_review",
        "camp_head": _git_head(ROOT),
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(execution),
        "reviewed_root_sha256": seal["root_sha256"],
        "planned_pair_count": 100,
        "planned_arm_run_count": 300,
        "terminal_arm_run_count": 300,
        "complete_arm_run_count": recorded["complete_arm_run_count"],
        "retained_fixed_dp_capability_failure_count": recorded[
            "retained_fixed_dp_capability_failure_count"
        ],
        "paired_eligible_pair_count": recorded["paired_eligible_pair_count"],
        "paired_eligible_rate": recorded["paired_eligible_rate"],
        "coverage_gate_passed": recorded["coverage_gate_passed"],
        "all_configs_independently_rebuilt": True,
        "all_terminal_rows_reconstructed": True,
        "all_complete_receipts_revalidated": True,
        "all_retained_k8_failures_recomputed": True,
        "all_initial_pair_resets_rechecked": True,
        "calibration_analysis_rederived": True,
        "atom_scores_and_selections_rederived": True,
        "candidate0_same_forward_operational_default": True,
        "candidate_tensor_modified": False,
        "training_or_model_change_executed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    _write_json(output / "report.json", review_report)
    (output / "HEADS").write_text(
        f"camp_head={review_report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (output / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output / "run.exit").write_text("0\n", encoding="ascii")
    return seal_artifact(output, label="V25 paired calibration execution review")


def _validate_report(report: Mapping[str, Any], *, execution: Path) -> None:
    fields = {
        "schema_version",
        "status",
        "fixed_dp_head",
        "pair_count",
        "planned_arm_run_count",
        "terminal_arm_run_count",
        "complete_arm_run_count",
        "retained_fixed_dp_capability_failure_count",
        "paired_eligible_pair_count",
        "paired_eligible_rate",
        "coverage_gate_passed",
        "run_results_sha256",
        "paired_calibration_corpus_sha256",
        "independent_reset_per_arm",
        "candidate0_same_forward_operational_default",
        "candidate_tensor_modified",
        "training_executed",
        "fresh_b2_opened",
        "fresh_outcome_fields_consumed",
        "artifact_schema_version",
        "camp_head",
        "device",
        "input_roots",
        "probe_template",
        "probe_template_sha256",
        "runtime_receipt_sha256_by_scenario",
        "runtime_selector_authority",
        "preregistration_root_sha256",
        "calibration_analysis_sha256",
        "atom_calibration_sha256",
        "model_loaded",
        "candidate_generation_executed",
        "independent_review_completed",
    }
    if set(report) != fields:
        raise ValueError("paired calibration execution report field set drifted")
    expected = {
        "schema_version": "camp_dp_v25_paired_calibration_execution_v1",
        "fixed_dp_head": FIXED_DP_HEAD,
        "pair_count": 100,
        "planned_arm_run_count": 300,
        "terminal_arm_run_count": 300,
        "independent_reset_per_arm": True,
        "candidate0_same_forward_operational_default": True,
        "candidate_tensor_modified": False,
        "training_executed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
        "artifact_schema_version": EXECUTION_SCHEMA_VERSION,
        "device": "cuda",
        "model_loaded": True,
        "candidate_generation_executed": True,
        "independent_review_completed": False,
    }
    if any(not _strict_equal(report.get(name), value) for name, value in expected.items()):
        raise ValueError("paired calibration execution report contract drifted")
    if report.get("status") not in {
        "passed_paired_calibration_execution",
        "paired_calibration_execution_scientifically_ineligible",
    }:
        raise ValueError("paired calibration execution status drifted")
    if type(report.get("input_roots")) is not dict or not (execution / "runs").is_dir():
        raise ValueError("paired calibration execution inventory is incomplete")


def _validate_heads(path: Path, report: Mapping[str, Any]) -> None:
    expected = (
        f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n"
    ).encode("ascii")
    if path.read_bytes() != expected:
        raise ValueError("paired calibration HEADS drifted")
    if report["camp_head"] != _git_head(ROOT):
        raise ValueError("paired calibration CAMP implementation HEAD drifted")


def _verify_input_roots(roots: Mapping[str, Any]) -> None:
    expected = {
        field
        for role in ROOT_ROLES_CONSUMED
        for field in (f"{role}_artifact", f"{role}_root_sha256")
    }
    if type(roots) is not dict or set(roots) != expected:
        raise ValueError("paired calibration consumed root field set drifted")
    for role in ROOT_ROLES_CONSUMED:
        artifact = Path(roots[f"{role}_artifact"]).resolve()
        verify_complete_seal(
            artifact,
            roots[f"{role}_root_sha256"],
            label=f"paired calibration {role}",
        )
        if (artifact / "run.exit").read_bytes() != b"0\n":
            raise ValueError(f"paired calibration {role} run.exit drifted")
    review_links = {
        "route_review": "route",
        "runtime_review": "runtime",
        "paired_plan_review": "paired_plan",
        "preregistration_review": "preregistration",
        "training_review": "training",
    }
    for review_role, source_role in review_links.items():
        payload = _canonical_json(Path(roots[f"{review_role}_artifact"]) / "report.json")
        if payload.get("reviewed_root_sha256") != roots[f"{source_role}_root_sha256"]:
            raise ValueError(f"paired calibration {review_role} cross-link drifted")


def _verify_preregistered_root_chain(
    preregistration: Mapping[str, Any], roots: Mapping[str, Any]
) -> None:
    bindings = preregistration["root_artifacts"]
    consumed_mapping = {
        "training": "training",
        "training_review": "training_review",
        "map": "map",
        "base_plan": "plan",
        "paired_plan": "paired_plan",
        "paired_plan_review": "paired_plan_review",
        "route": "route",
        "route_review": "route_review",
        "runtime": "runtime",
        "runtime_review": "runtime_review",
    }
    for prereg_role, consumed_role in consumed_mapping.items():
        expected = {
            "path": str(Path(roots[f"{consumed_role}_artifact"]).resolve()),
            "root_sha256": roots[f"{consumed_role}_root_sha256"],
        }
        actual = {
            "path": str(Path(bindings[prereg_role]["path"]).resolve()),
            "root_sha256": bindings[prereg_role]["root_sha256"],
        }
        if not _strict_equal(actual, expected):
            raise ValueError(f"paired calibration preregistered {prereg_role} drifted")
    for role in ROOT_ROLES:
        binding = bindings[role]
        artifact = Path(binding["path"]).resolve()
        verify_complete_seal(
            artifact,
            binding["root_sha256"],
            label=f"paired calibration preregistered {role}",
        )
        if (artifact / "run.exit").read_bytes() != b"0\n":
            raise ValueError(f"paired calibration preregistered {role} run.exit drifted")


def _selector_authority(assets: Any, roots: Mapping[str, Any]) -> dict[str, Any]:
    training = Path(roots["training_artifact"])
    return {
        "training_artifact": {
            "path": str(training.resolve()),
            "root_sha256": roots["training_root_sha256"],
        },
        "training_review_artifact": {
            "path": str(Path(roots["training_review_artifact"]).resolve()),
            "root_sha256": roots["training_review_root_sha256"],
        },
        "model_registry_sha256": _sha256(training / "model_registry.json"),
        "training_scale_sha256": assets.atom_scales_sha256,
        "context_scaler_sha256": assets.scene14d_weight_provider.context_scaler_sha256,
        "atom_scales": {
            "path": str((training / "runtime_atom_scales.json").resolve()),
            "sha256": assets.atom_scales_sha256,
        },
        "static14d_weights": {
            "path": str((training / "static14d_runtime_weights.npy").resolve()),
            "sha256": assets.static14d_weights_sha256,
        },
    }


def _verify_model_preregistration(
    preregistration: Mapping[str, Any], selector: Mapping[str, Any], assets: Any
) -> None:
    model = preregistration["model_authority"]
    expected = {
        "model_registry_sha256": selector["model_registry_sha256"],
        "training_scale_sha256": selector["training_scale_sha256"],
        "context_scaler_sha256": selector["context_scaler_sha256"],
        "atom_scales_file_sha256": assets.atom_scales_sha256,
        "static14d_weights_file_sha256": assets.static14d_weights_sha256,
        "scene14d_theta_sha256": assets.scene14d_weight_provider.theta_sha256,
    }
    if not _strict_equal(model, expected):
        raise ValueError("paired calibration preregistered model authority drifted")


def _review_terminal_metadata(
    result: Mapping[str, Any],
    *,
    ordinal: int,
    unit: Mapping[str, Any],
    identity: Mapping[str, Any],
    arm_order_index: int,
    plan_arm: str,
) -> None:
    common = {
        "schema_version": RUN_RESULT_SCHEMA_VERSION,
        "run_ordinal": ordinal,
        "unit_ordinal": unit["unit_ordinal"],
        "unit_sha256": unit["unit_sha256"],
        "arm_order_index": arm_order_index,
        "plan_arm": plan_arm,
        "scenario_identity_sha256": unit["scenario_identity_sha256"],
        "route_identity_sha256": identity["route_identity_sha256"],
        "scenario_family": identity["scenario_family"],
        "risk_tier": identity["risk_tier"],
        "benchmark_stratum": identity["benchmark_stratum"],
        "signal_source_class": identity["signal_source_class"],
        "phase_authority_mode": identity["phase_authority_mode"],
        "semantic_parameter_block_sha256": identity[
            "semantic_parameter_block_sha256"
        ],
        "seed": unit["seed"],
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    for name, value in common.items():
        if not _strict_equal(result.get(name), value):
            raise ValueError(f"paired calibration terminal {name} drifted")
    if result["status"] == "complete":
        extra = {
            "map_sha256": identity["map_sha256"],
            "intersection_sha256": identity["intersection_sha256"],
            "corridor_sha256": identity["corridor_sha256"],
            "route_family_sha256": identity["route_family_sha256"],
        }
        for name, value in extra.items():
            if result.get(name) != value:
                raise ValueError(f"paired calibration complete {name} drifted")
        expected_fields = set(common) | set(extra) | {
            "status",
            "native_receipt",
            "failure_receipt",
        }
    else:
        expected_fields = set(common) | {
            "status",
            "native_receipt",
            "failure_receipt",
        }
    if set(result) != expected_fields:
        raise ValueError("paired calibration terminal field set drifted")


def _review_complete(
    *,
    execution: Path,
    run_dir: Path,
    result: Mapping[str, Any],
    unit: Mapping[str, Any],
    identity: Mapping[str, Any],
    route_asset: Mapping[str, Any],
    plan_arm: str,
) -> dict[str, Any] | None:
    native = result.get("native_receipt")
    if type(native) is not dict or result.get("failure_receipt") is not None:
        raise ValueError("complete paired calibration terminal evidence drifted")
    native_arm = "dp" if plan_arm == ARMS[0] else "camp"
    validate_native_arm_receipt(
        native,
        native_arm,
        expected_ticks=64,
        expected_selection_policy=("v22_source_valid" if native_arm == "camp" else None),
        expected_safety_schema="safety_cost_native_v22",
    )
    if (
        native.get("fixed_dp_head") != FIXED_DP_HEAD
        or native.get("route_name") != identity["route_identity_sha256"]
        or native.get("route_sha256") != route_asset["sha256"]
        or native.get("scenario_seed") != unit["seed"]
        or native.get("claim_authorized") is not False
    ):
        raise ValueError("complete paired calibration native authority drifted")
    evidence_path = run_dir / "decision_evidence.json"
    evidence = _canonical_value(evidence_path)
    expected_count = 0 if native_arm == "dp" else 64
    if (
        type(evidence) is not list
        or len(evidence) != expected_count
        or native.get("calibration_decision_evidence_sha256")
        != _sha256(evidence_path)
        or native.get("calibration_decision_evidence_count") != expected_count
    ):
        raise ValueError("paired calibration decision evidence binding drifted")
    ticks = native["ticks"]
    if plan_arm == ARMS[0]:
        if any(tick["selected_index"] != 0 for tick in ticks):
            raise ValueError("paired calibration candidate0 selected index drifted")
        return None
    if plan_arm == ARMS[1]:
        if any(tick.get("v25_scene_selector") is not None for tick in ticks):
            raise ValueError("paired calibration Static14D consumed Scene weights")
    else:
        for tick in ticks:
            context = tick.get("v25_context")
            source = context.get("source_receipt") if type(context) is dict else None
            if (
                type(tick.get("v25_scene_selector")) is not dict
                or type(source) is not dict
                or source.get("phase_remaining_available") is not False
            ):
                raise ValueError("paired calibration Scene14D no-V2I drifted")
    return {
        "plan_arm": plan_arm,
        "snapshots": evidence,
        "native_ticks": ticks,
        "scenario_family": identity["scenario_family"],
        "risk_tier": identity["risk_tier"],
        "signal_source_class": identity["signal_source_class"],
    }


def _review_failure(
    execution: Path,
    *,
    run_dir: Path,
    result: Mapping[str, Any],
    unit: Mapping[str, Any],
    identity: Mapping[str, Any],
    plan_arm: str,
) -> None:
    if (run_dir / "decision_evidence.json").exists():
        raise ValueError("retained K8 failure unexpectedly has decision evidence")
    summary = result.get("failure_receipt")
    if type(summary) is not dict or result.get("native_receipt") is not None:
        raise ValueError("retained K8 failure terminal evidence drifted")
    digest = summary.get("raw_failure_receipt_sha256")
    details = [
        path
        for path in (execution / "fixed_dp_capability_failures").glob("*.json")
        if _sha256(path) == digest
    ]
    if len(details) != 1:
        raise ValueError("retained K8 failure detail binding drifted")
    detail = _canonical_json(details[0])
    raw_info = detail.get("raw_preimage")
    if type(raw_info) is not dict:
        raise ValueError("retained K8 failure raw preimage is missing")
    raw_path = (execution / raw_info["relative_path"]).resolve()
    if execution not in raw_path.parents or _sha256(raw_path) != raw_info["file_sha256"]:
        raise ValueError("retained K8 failure raw preimage drifted")
    raw = raw_path.read_bytes()
    if len(raw) != 8 * 80 * 4 * 4:
        raise ValueError("retained K8 failure raw preimage size drifted")
    candidates = np.frombuffer(raw, dtype=np.float32).copy().reshape(8, 80, 4)
    try:
        validate_fixed_k8_candidate_tensor(
            candidates,
            tick_index=detail["tick_index"],
            default_output_sha256=detail["default_output_sha256"],
            default_candidate0_identity=detail["default_candidate0_identity"],
        )
    except FixedDpCandidateGenerationCapabilityFailure as failure:
        metadata = failure.canonical_metadata()
    else:
        raise ValueError("retained K8 failure no longer reproduces")
    for name, value in metadata.items():
        if not _strict_equal(detail.get(name), value):
            raise ValueError("retained K8 failure metadata drifted")
    exact = {
        "schema_version": FAILURE_SCHEMA_VERSION,
        "run_ordinal": result["run_ordinal"],
        "unit_ordinal": unit["unit_ordinal"],
        "scenario_identity_sha256": identity["scenario_identity_sha256"],
        "route_identity_sha256": identity["route_identity_sha256"],
        "map_sha256": identity["map_sha256"],
        "intersection_sha256": identity["intersection_sha256"],
        "corridor_sha256": identity["corridor_sha256"],
        "route_family_sha256": identity["route_family_sha256"],
        "plan_arm": plan_arm,
        "seed": unit["seed"],
        "fixed_dp_head": FIXED_DP_HEAD,
        "training_eligible": False,
        "calibration_eligible": False,
        "evaluation_eligible": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
        **metadata,
        "raw_preimage": {
            "relative_path": raw_info["relative_path"],
            "file_sha256": raw_info["file_sha256"],
            "shape": [8, 80, 4],
            "dtype": "float32",
        },
    }
    if not _strict_equal(detail, exact):
        raise ValueError("retained K8 failure detail drifted")
    expected_summary = {
        "schema_version": FAILURE_SCHEMA_VERSION,
        "failure_class": metadata["failure_class"],
        "reason": metadata["reason"],
        "raw_failure_receipt_sha256": digest,
        "training_eligible": False,
        "calibration_eligible": False,
        "evaluation_eligible": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    if not _strict_equal(summary, expected_summary):
        raise ValueError("retained K8 failure summary drifted")


def _review_initial_pairing(
    pairs: Mapping[int, Mapping[str, Mapping[str, Any]]]
) -> None:
    if set(pairs) != set(range(100)):
        raise ValueError("paired calibration pair inventory drifted")
    for ordinal in range(100):
        rows = pairs[ordinal]
        if set(rows) != set(ARMS):
            raise ValueError("paired calibration arm inventory drifted")
        if not all(row["status"] == "complete" for row in rows.values()):
            continue
        natives = [rows[arm]["native_receipt"] for arm in ARMS]
        for name in ("route_sha256", "initial_state_sha256", "initial_input_sha256"):
            values = [native.get(name) for native in natives]
            if any(type(value) is not str for value in values) or len(set(values)) != 1:
                raise ValueError(f"paired calibration initial {name} drifted")
        ticks0 = [native["ticks"][0] for native in natives]
        for name in (
            "input_sha256",
            "candidate_tensor_sha256_before",
            "default_output_sha256",
            "candidate_row_sha256",
        ):
            values = [tick.get(name) for tick in ticks0]
            if not all(_strict_equal(values[0], value) for value in values[1:]):
                raise ValueError(f"paired calibration tick0 {name} drifted")


def _independent_corpus(
    plan: Mapping[str, Any], results: list[Mapping[str, Any]]
) -> dict[str, Any]:
    if len(results) != 300:
        raise ValueError("paired calibration requires 300 terminal rows")
    identities = {
        row["scenario_identity_sha256"]: row for row in plan["identities"]
    }
    by_pair: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    complete_by_arm: Counter[str] = Counter()
    failure_by_arm: Counter[str] = Counter()
    ordinal = 0
    for unit in plan["execution_units"]:
        for arm_order_index, arm in enumerate(unit["ordered_arms"]):
            row = results[ordinal]
            if (
                row["run_ordinal"] != ordinal
                or row["unit_ordinal"] != unit["unit_ordinal"]
                or row["unit_sha256"] != unit["unit_sha256"]
                or row["arm_order_index"] != arm_order_index
                or row["plan_arm"] != arm
            ):
                raise ValueError("paired calibration result order drifted")
            by_pair[unit["unit_ordinal"]].append(row)
            (complete_by_arm if row["status"] == "complete" else failure_by_arm)[arm] += 1
            ordinal += 1
    eligible = {
        unit for unit, rows in by_pair.items() if all(row["status"] == "complete" for row in rows)
    }
    family_denominator: Counter[str] = Counter()
    family_eligible: Counter[str] = Counter()
    source_denominator: Counter[str] = Counter()
    source_eligible: Counter[str] = Counter()
    family_tier_denominator: Counter[str] = Counter()
    family_tier_eligible: Counter[str] = Counter()
    for unit in plan["execution_units"]:
        identity = identities[unit["scenario_identity_sha256"]]
        family = identity["scenario_family"]
        source = identity["signal_source_class"]
        family_tier = f"{family}/{identity['risk_tier']}"
        family_denominator[family] += 1
        source_denominator[source] += 1
        family_tier_denominator[family_tier] += 1
        if unit["unit_ordinal"] in eligible:
            family_eligible[family] += 1
            source_eligible[source] += 1
            family_tier_eligible[family_tier] += 1
    family_rates = {
        key: family_eligible[key] / value for key, value in sorted(family_denominator.items())
    }
    source_rates = {
        key: source_eligible[key] / value for key, value in sorted(source_denominator.items())
    }
    family_tier_rates = {
        key: family_tier_eligible[key] / value
        for key, value in sorted(family_tier_denominator.items())
    }
    pair_rate = len(eligible) / 100
    coverage = bool(
        pair_rate >= 0.95
        and all(value > 0.90 for value in family_rates.values())
        and all(value > 0.90 for value in source_rates.values())
        and all(value > 0.80 for value in family_tier_rates.values())
        and all(value > 0.0 for value in family_tier_rates.values())
    )
    complete_count = sum(row["status"] == "complete" for row in results)
    return {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "status": (
            "passed_paired_calibration_corpus"
            if coverage
            else "paired_calibration_corpus_scientifically_ineligible"
        ),
        "fixed_dp_head": FIXED_DP_HEAD,
        "map_count": plan["map_count"],
        "intersection_count": plan["intersection_count"],
        "corridor_count": plan["corridor_count"],
        "route_count": plan["route_count"],
        "pair_count": 100,
        "planned_arm_run_count": 300,
        "terminal_arm_run_count": 300,
        "complete_arm_run_count": complete_count,
        "retained_fixed_dp_capability_failure_count": 300 - complete_count,
        "complete_count_by_arm": dict(sorted(complete_by_arm.items())),
        "failure_count_by_arm": dict(sorted(failure_by_arm.items())),
        "paired_eligible_pair_count": len(eligible),
        "paired_eligible_rate": pair_rate,
        "minimum_overall_paired_eligible_rate": 0.95,
        "minimum_family_and_source_rate_exclusive": 0.90,
        "minimum_family_tier_rate_exclusive": 0.80,
        "family_paired_eligible_rates": family_rates,
        "source_paired_eligible_rates": source_rates,
        "family_tier_paired_eligible_rates": family_tier_rates,
        "coverage_gate_passed": coverage,
        "all_failures_retained_in_denominator": True,
        "complete_case_filtering": False,
        "candidate0_semantics": "same_forward_operational_default_alias",
        "candidate_tensor_modified": False,
        "training_executed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
        "arm_results": results,
    }


def _verify_report_accounting(
    report: Mapping[str, Any],
    *,
    results: list[Mapping[str, Any]],
    corpus: Mapping[str, Any],
    analysis_path: Path,
    atom_path: Path,
) -> None:
    expected = {
        "complete_arm_run_count": corpus["complete_arm_run_count"],
        "retained_fixed_dp_capability_failure_count": corpus[
            "retained_fixed_dp_capability_failure_count"
        ],
        "paired_eligible_pair_count": corpus["paired_eligible_pair_count"],
        "paired_eligible_rate": corpus["paired_eligible_rate"],
        "coverage_gate_passed": corpus["coverage_gate_passed"],
        "run_results_sha256": _canonical_sha(results),
        "paired_calibration_corpus_sha256": _canonical_sha(corpus),
        "calibration_analysis_sha256": _sha256(analysis_path),
        "atom_calibration_sha256": _sha256(atom_path),
        "preregistration_root_sha256": report["input_roots"][
            "preregistration_root_sha256"
        ],
    }
    for name, value in expected.items():
        if not _strict_equal(report.get(name), value):
            raise ValueError(f"paired calibration report {name} drifted")


def _seal_failure(output: Path, exc: BaseException) -> None:
    if output.exists():
        raise exc
    output.mkdir(parents=True)
    _write_json(
        output / "failure.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "failed_independent_paired_calibration_execution_review",
            "reason": str(exc),
            "fresh_b2_opened": False,
            "fresh_outcome_fields_consumed": [],
        },
    )
    (output / "HEADS").write_text(
        f"camp_head={_git_head(ROOT)}\nfixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (output / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output / "run.exit").write_text("1\n", encoding="ascii")
    seal_artifact(output, label="failed V25 paired calibration execution review")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--artifact-root-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = review(**vars(args))
    except BaseException as exc:
        _seal_failure(args.output_dir.resolve(), exc)
        raise
    print(json.dumps({"status": "sealed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
