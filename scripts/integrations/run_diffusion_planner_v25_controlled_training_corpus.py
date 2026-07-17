#!/usr/bin/env python3
"""Preflight and execute the frozen V25 controlled train corpus."""

from __future__ import annotations

import argparse
import collections
from contextlib import contextmanager, nullcontext
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Iterator, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v25_context import (  # noqa: E402
    CONTEXT_SCHEMA_VERSION,
    RAW_FEATURE_NAMES,
)
from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (  # noqa: E402
    SCENARIO_FAMILIES,
    V25ControlledSceneAdapter,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
    build_native_arm_runner,
    validate_native_arm_receipt,
    validate_v25_controlled_train_config,
    verify_config_assets,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_scenario_phase import (  # noqa: E402
    FORMAL_FORBIDDEN_SEEDS,
    _file_sha256,
    _load_json,
    _materialize_routes,
    _seal,
    _verify_seal,
    _write_json,
)


SCHEMA_VERSION = "camp_dp_v25_controlled_training_corpus_execution_v2"
SNAPSHOT_SCHEMA_VERSION = "camp_dp_v25_controlled_train_snapshot_v2"
FORMAL_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_controlled_corpus_source_freeze_retry2_ff028387_"
    "20260717T140842CST"
)
FORMAL_ROOT_SHA256 = (
    "c4dbd49c5fde36302046c6386ca1b8d9cdcaa922976f08230e6227962cc1e531"
)
EXPECTED_TEMPLATE_SHA256 = (
    "1e734165f7a614e93019df0a5c22b5e36722298cb50b21c5ce8fd0e4e2cf82bc"
)
EXPECTED_EXECUTABLE_IDENTITIES = 1500
EXPECTED_RETAINED_INELIGIBLE = 153
EXPECTED_SEED = 25001
CORPUS_STEPS = 64
MINIMUM_FREE_BYTES = 10 * 1024**3
TRAIN_LOCK = Path("/root/autodl-tmp/.camp_dp_v25_controlled_train_corpus.lock")
SUPERSEDED_PARTIAL_CORPUS_ROOT = (
    "a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481"
)
CORRECTED_GENERATION_SCALES = (
    ROOT
    / "configs"
    / "integrations"
    / "diffusion_planner_v25_atom_scales_correction_v2.json"
)


class ArtifactContractViolation(RuntimeError):
    """A non-retainable scientific or artifact invariant failed."""


def validate_identity_terminal(
    *,
    status: str,
    receipt_tick_count: int,
    snapshot_count: int,
    context_count: int,
    failure_type: str | None,
    failure_reason: str | None,
) -> str:
    counts = (receipt_tick_count, snapshot_count, context_count)
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts):
        raise ArtifactContractViolation("identity counts must be nonnegative integers")
    if status == "complete":
        if counts != (CORPUS_STEPS, CORPUS_STEPS, CORPUS_STEPS):
            raise ArtifactContractViolation(
                "a complete identity must contain exactly 64 receipt, snapshot, "
                "and context ticks"
            )
        if failure_type is not None or failure_reason is not None:
            raise ArtifactContractViolation("complete identity carries failure metadata")
        return "complete"
    if status != "failed":
        raise ArtifactContractViolation("identity status is neither complete nor failed")
    if any(counts):
        raise ArtifactContractViolation(
            "partial snapshots are forbidden and make the artifact ineligible"
        )
    if (
        failure_type == "RetainedScenarioCapabilityFailure"
        and isinstance(failure_reason, str)
        and failure_reason.startswith("preregistered_scenario_capability:")
    ):
        return "retained_capability_failure"
    raise ArtifactContractViolation(
        "only an explicit preregistered scenario-capability failure may be retained"
    )


def validate_terminal_acceptance(
    results: list[Mapping[str, Any]],
    *,
    snapshot_index_count: int,
    expected_identity_count: int = EXPECTED_EXECUTABLE_IDENTITIES,
) -> dict[str, int]:
    if len(results) != expected_identity_count:
        raise ArtifactContractViolation(
            "terminal identity denominator is incomplete"
        )
    complete = 0
    retained_capability = 0
    for row in results:
        status = str(row.get("status"))
        snapshot_count = row.get("snapshot_count")
        if status == "complete":
            if snapshot_count != CORPUS_STEPS:
                raise ArtifactContractViolation(
                    "terminal complete identity does not contain exactly 64 ticks"
                )
            complete += 1
        elif (
            status == "failed"
            and snapshot_count == 0
            and row.get("failure_type") == "RetainedScenarioCapabilityFailure"
            and isinstance(row.get("failure_reason"), str)
            and str(row["failure_reason"]).startswith(
                "preregistered_scenario_capability:"
            )
        ):
            retained_capability += 1
        else:
            raise ArtifactContractViolation(
                "terminal results contain an illegal failure or partial identity"
            )
    expected_snapshots = complete * CORPUS_STEPS
    if snapshot_index_count != expected_snapshots:
        raise ArtifactContractViolation(
            "terminal snapshot index does not match complete identities"
        )
    return {
        "complete_identity_count": complete,
        "retained_capability_failure_count": retained_capability,
        "training_snapshot_count": expected_snapshots,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--preflight-artifact", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError(f"output already exists: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    lock_scope = (
        _exclusive_lock(TRAIN_LOCK) if args.execute else nullcontext()
    )
    with lock_scope:
        try:
            report = _run(args)
            _write_json(args.output_dir / "report.json", report)
            (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
            root_sha = _seal(args.output_dir)
            print(
                json.dumps(
                    {
                        "status": report["status"],
                        "mode": report["mode"],
                        "output_dir": str(args.output_dir),
                        "root_sha256": root_sha,
                        "attempted_identity_count": report.get(
                            "attempted_identity_count", 0
                        ),
                        "snapshot_count": report.get("snapshot_count", 0),
                    },
                    sort_keys=True,
                )
            )
        except BaseException as exc:
            _write_json(
                args.output_dir / "failure.json",
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "failed",
                    "failure_type": type(exc).__name__,
                    "failure_reason": str(exc),
                    "fresh_b_opened": False,
                    "outcome_fields_consumed": [],
                    "seal_passed": False,
                },
            )
            (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
            _seal(args.output_dir)
            raise


def _run(args: argparse.Namespace) -> dict[str, Any]:
    camp_head = _git_head(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree is dirty")
    if _git_head(args.dp_repo) != FIXED_DP_HEAD or _tracked_dirty(args.dp_repo):
        raise ValueError("fixed DP drifted or has tracked modifications")
    if shutil.disk_usage(args.output_dir.parent).free < MINIMUM_FREE_BYTES:
        raise RuntimeError("free disk is below the 10 GiB floor")

    plan, formal_receipt = _load_formal_plan()
    if _file_sha256(args.probe_template) != EXPECTED_TEMPLATE_SHA256:
        raise ValueError("probe template SHA256 mismatch")
    template = _load_json(args.probe_template)
    cases = [case for case in plan["train"] if case["runner_eligible"]]
    route_assets = _materialize_routes(
        cases, args.output_dir / "routes", args.dp_repo
    )
    common = {
        "schema_version": SCHEMA_VERSION,
        "camp_head": camp_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "formal_artifact": str(FORMAL_ARTIFACT),
        "formal_root_sha256": formal_receipt,
        "probe_template": str(args.probe_template),
        "probe_template_sha256": EXPECTED_TEMPLATE_SHA256,
        "train_lock": str(TRAIN_LOCK),
        "minimum_free_bytes": MINIMUM_FREE_BYTES,
        "rejected_roots": [SUPERSEDED_PARTIAL_CORPUS_ROOT],
        "terminal_lock_scope": "execution_through_progress_report_run_exit_and_seal",
        "free_bytes_at_start": shutil.disk_usage(args.output_dir.parent).free,
        "fresh_b_opened": False,
        "outcome_fields_consumed": [],
    }
    _write_json(args.output_dir / "source_receipt.json", common)
    (args.output_dir / "HEADS").write_text(
        f"camp_source_head={camp_head}\nfixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (args.output_dir / "COMMAND").write_text(
        " ".join(sys.argv) + "\n", encoding="utf-8"
    )

    if args.preflight:
        if args.preflight_artifact is not None:
            raise ValueError("preflight must not consume a prior preflight artifact")
        return _preflight(cases, template, route_assets, common)
    if args.preflight_artifact is None:
        raise ValueError("execution requires --preflight-artifact")
    preflight = _verify_preflight(args.preflight_artifact, camp_head)
    return _execute(
        cases=cases,
        template=template,
        route_assets=route_assets,
        common=common,
        preflight=preflight,
        preflight_artifact=args.preflight_artifact,
        device=args.device,
        output_dir=args.output_dir,
    )


def build_controlled_train_config(
    template: Mapping[str, Any],
    case: Mapping[str, Any],
    route_asset: Mapping[str, str],
) -> dict[str, Any]:
    config = json.loads(json.dumps(template))
    identity = str(case["route_identity_sha256"])
    seed_values = case.get("seeds")
    if seed_values != [EXPECTED_SEED]:
        raise ValueError("controlled train case seed drifted")
    config["schema_version"] = "camp_dp_v25_controlled_train_v2"
    config["map"] = {
        "path": str(case["source_map_path"]),
        "sha256": str(case["source_map_sha256"]),
    }
    config["routes"] = [
        {
            "name": identity,
            "path": str(route_asset["path"]),
            "sha256": str(route_asset["sha256"]),
        }
    ]
    config["seeds"] = {
        "scenario": EXPECTED_SEED,
        "candidate": EXPECTED_SEED,
        "bootstrap": EXPECTED_SEED,
        "formal_forbidden": list(FORMAL_FORBIDDEN_SEEDS),
    }
    config["selector"]["role"] = (
        "v25_controlled_train_fixed_static_behavior_policy"
    )
    config["selector"]["atom_scales"] = {
        "path": str(CORRECTED_GENERATION_SCALES),
        "sha256": _file_sha256(CORRECTED_GENERATION_SCALES),
    }
    config["selector"]["normalization_contract"] = (
        "z=clip(raw_atom/generation_behavior_scale,0,10)"
    )
    config["selector"]["tie_break_contract"] = (
        "lowest_eligible_candidate_index"
    )
    config["selector"]["atom_scale_contract"] = (
        "camp_dp_v25_generation_behavior_atom_scales_v2"
    )
    config["spawn_config"].update(
        {
            "seed": EXPECTED_SEED,
            "max_steps": CORPUS_STEPS,
            "max_active_npcs": 0,
            "spawn_probability": 0.0,
            "static_npc_count": 0,
            "parked_vehicles_yaml": None,
            "ego_init_speed": float(case["parameters"]["ego_speed_mps"]),
        }
    )
    config["protocol"] = {
        "arm_order": ["camp"],
        "route_order": [identity],
        "corpus_steps": CORPUS_STEPS,
        "sample_every_ticks": 1,
        "padding_policy": "native_zero_left_pad_to_31_v1",
        "safety_schema": "safety_cost_native_v22",
        "route_role": "v25_controlled_outcome_blind_train_corpus",
        "candidate_k": 8,
        "claim_authorized": False,
        "training_data_generation_authorized": True,
        "selector_training_execution_authorized": False,
        "calibration_authorized": False,
        "holdout_access_authorized": False,
        "fresh_b_opened": False,
        "outcomes_used_for_selection": False,
        "context_schema_version": CONTEXT_SCHEMA_VERSION,
        "context_mode": "no_v2i",
    }
    config["controlled_scenario"] = json.loads(json.dumps(case))
    validate_v25_controlled_train_config(config)
    return config


def _load_formal_plan() -> tuple[dict[str, Any], str]:
    if not FORMAL_ARTIFACT.is_dir():
        raise FileNotFoundError(FORMAL_ARTIFACT)
    root = _verify_seal(FORMAL_ARTIFACT)
    if root != FORMAL_ROOT_SHA256:
        raise ValueError("formal controlled-corpus root drifted")
    report = _load_json(FORMAL_ARTIFACT / "report.json")
    plan = _load_json(FORMAL_ARTIFACT / "controlled_corpus_final_plan.json")
    if (
        report.get("status") != "passed"
        or report.get("mode") != "freeze_formal"
        or plan.get("schema_version")
        != "camp_dp_v25_controlled_corpus_final_plan_v1"
        or plan.get("outcome_blind") is not True
        or plan.get("outcome_fields_consumed") != []
        or plan.get("fresh_b_outcome_opened") is not False
    ):
        raise ValueError("formal controlled-corpus authority is invalid")
    executable = [case for case in plan["train"] if case["runner_eligible"]]
    ineligible = [case for case in plan["train"] if not case["runner_eligible"]]
    if (
        len(executable) != EXPECTED_EXECUTABLE_IDENTITIES
        or len(ineligible) != EXPECTED_RETAINED_INELIGIBLE
        or any(case.get("retention_role") != "executable" for case in executable)
        or any(
            case.get("retention_role") != "source_ineligible_retained"
            for case in ineligible
        )
        or any(case.get("split") != "train" for case in plan["train"])
    ):
        raise ValueError("formal controlled-train denominator drifted")
    return plan, root


def _preflight(
    cases: list[dict[str, Any]],
    template: Mapping[str, Any],
    route_assets: Mapping[str, Mapping[str, str]],
    common: Mapping[str, Any],
) -> dict[str, Any]:
    if not _lock_is_free(TRAIN_LOCK):
        raise RuntimeError("controlled train corpus lock is held")
    shared = None
    seen_routes: set[str] = set()
    seen_maps: set[str] = set()
    receipts = []
    for case in cases:
        identity = str(case["route_identity_sha256"])
        config = build_controlled_train_config(template, case, route_assets[identity])
        if shared is None:
            verify_config_assets(config)
            shared = _shared_assets(config)
        elif _shared_assets(config) != shared:
            raise ValueError("fixed DP or behavior-policy assets changed")
        _verify_case_assets_cached(config, seen_routes=seen_routes, seen_maps=seen_maps)
        receipts.append(
            {
                "scenario_id": case["scenario_id"],
                "family": case["family"],
                "tier": case["tier"],
                "route_identity_sha256": identity,
                "seed": EXPECTED_SEED,
                "config_sha256": _canonical_sha256(config),
            }
        )
    return {
        **dict(common),
        "mode": "preflight",
        "status": "passed",
        "validated_identity_count": len(receipts),
        "source_ineligible_retained_identity_count": EXPECTED_RETAINED_INELIGIBLE,
        "formal_train_manifest_identity_count": (
            len(receipts) + EXPECTED_RETAINED_INELIGIBLE
        ),
        "unique_route_count": len(seen_routes),
        "family_counts": dict(collections.Counter(case["family"] for case in cases)),
        "tier_counts": dict(collections.Counter(case["tier"] for case in cases)),
        "corpus_steps": CORPUS_STEPS,
        "snapshot_capacity": len(cases) * CORPUS_STEPS,
        "model_loaded": False,
        "candidate_generation_started": False,
        "simulator_started": False,
        "training_executed": False,
        "calibration_executed": False,
        "fresh_b_opened": False,
        "outcome_fields_consumed": [],
        "claim_authorized": False,
        "config_receipts": receipts,
    }


def _verify_preflight(path: Path, camp_head: str) -> dict[str, Any]:
    root = _verify_seal(path)
    report = _load_json(path / "report.json")
    if (
        report.get("status") != "passed"
        or report.get("mode") != "preflight"
        or report.get("camp_head") != camp_head
        or report.get("formal_root_sha256") != FORMAL_ROOT_SHA256
        or report.get("validated_identity_count") != EXPECTED_EXECUTABLE_IDENTITIES
        or report.get("fresh_b_opened") is not False
        or report.get("outcome_fields_consumed") != []
    ):
        raise ValueError("controlled train preflight authority is invalid")
    return {"path": str(path), "root_sha256": root}


def _execute(
    *,
    cases: list[dict[str, Any]],
    template: Mapping[str, Any],
    route_assets: Mapping[str, Mapping[str, str]],
    common: Mapping[str, Any],
    preflight: Mapping[str, Any],
    preflight_artifact: Path,
    device: str,
    output_dir: Path,
) -> dict[str, Any]:
    first = cases[0]
    first_config = build_controlled_train_config(
        template, first, route_assets[str(first["route_identity_sha256"])]
    )
    runner = build_native_arm_runner(first_config, device=device)
    snapshots_dir = output_dir / "snapshots"
    snapshots_dir.mkdir()
    results_path = output_dir / "results.jsonl"
    index_path = output_dir / "snapshot_index.jsonl"
    progress_path = output_dir / "progress.json"
    results: list[dict[str, Any]] = []
    snapshot_count = 0
    started = time.perf_counter()
    # main() owns TRAIN_LOCK across execution, terminal progress/report,
    # run.exit, and seal. Keep this structural scope for the nested streams.
    with nullcontext():
        with results_path.open("w", encoding="utf-8", newline="\n") as result_file:
            with index_path.open("w", encoding="utf-8", newline="\n") as index_file:
                for ordinal, case in enumerate(cases):
                    if shutil.disk_usage(output_dir.parent).free < MINIMUM_FREE_BYTES:
                        raise RuntimeError("free disk fell below the 10 GiB floor")
                    identity = str(case["route_identity_sha256"])
                    config = build_controlled_train_config(
                        template, case, route_assets[identity]
                    )
                    adapter = V25ControlledSceneAdapter(case)
                    snapshots: list[Mapping[str, Any]] = []
                    contexts: list[Mapping[str, Any]] = []
                    case_started = time.perf_counter()
                    status = "complete"
                    failure_type = None
                    failure_reason = None
                    receipt_tick_count = 0
                    try:
                        receipt = runner(
                            route=config["routes"][0],
                            arm="camp",
                            config=config,
                            output_dir=(
                                output_dir / "native_runs" / str(case["scenario_id"])
                            ),
                            max_steps=CORPUS_STEPS,
                            decision_sink=snapshots.append,
                            scene_adapter=adapter,
                            v25_context_sink=contexts.append,
                        )
                        receipt_tick_count = len(receipt.get("ticks", []))
                        validate_native_arm_receipt(
                            receipt,
                            "camp",
                            expected_ticks=receipt_tick_count,
                            require_summary=False,
                            expected_selection_policy="v22_source_valid",
                            expected_safety_schema="safety_cost_native_v22",
                        )
                    except Exception as exc:
                        status = "failed"
                        failure_type = type(exc).__name__
                        failure_reason = str(exc)
                    disposition = validate_identity_terminal(
                        status=status,
                        receipt_tick_count=receipt_tick_count,
                        snapshot_count=len(snapshots),
                        context_count=len(contexts),
                        failure_type=failure_type,
                        failure_reason=failure_reason,
                    )
                    payloads = []
                    if disposition == "complete":
                        for tick_index in range(CORPUS_STEPS):
                            payloads.append(combine_snapshot_context(
                            snapshot=snapshots[tick_index],
                            context=contexts[tick_index],
                            case=case,
                            tick_index=tick_index,
                            ))
                    paired_count = len(payloads)
                    for tick_index, payload in enumerate(payloads):
                        data = _canonical_json_bytes(payload) + b"\n"
                        digest = hashlib.sha256(data).hexdigest()
                        relative = Path("snapshots") / f"{digest}.json"
                        target = output_dir / relative
                        if target.exists() and target.read_bytes() != data:
                            raise ValueError("content-addressed snapshot collision")
                        if not target.exists():
                            target.write_bytes(data)
                        index_file.write(
                            json.dumps(
                                {
                                    "scenario_id": case["scenario_id"],
                                    "tick_index": tick_index,
                                    "relative_path": relative.as_posix(),
                                    "sha256": digest,
                                },
                                sort_keys=True,
                            )
                            + "\n"
                        )
                    index_file.flush()
                    snapshot_count += paired_count
                    result = {
                        "ordinal": ordinal,
                        "scenario_id": case["scenario_id"],
                        "family": case["family"],
                        "tier": case["tier"],
                        "route_identity_sha256": identity,
                        "seed": EXPECTED_SEED,
                        "status": status,
                        "snapshot_count": paired_count,
                        "failure_type": failure_type,
                        "failure_reason": failure_reason,
                        "wall_seconds": time.perf_counter() - case_started,
                        "retained": True,
                        "outcome_fields_consumed": [],
                        "fresh_b_opened": False,
                    }
                    results.append(result)
                    result_file.write(json.dumps(result, sort_keys=True) + "\n")
                    result_file.flush()
                    _write_json_atomic(
                        progress_path,
                        {
                            "schema_version": SCHEMA_VERSION,
                            "status": "running",
                            "completed": ordinal + 1,
                            "total": len(cases),
                            "complete": sum(r["status"] == "complete" for r in results),
                            "failed": sum(r["status"] == "failed" for r in results),
                            "snapshot_count": snapshot_count,
                            "last_scenario_id": case["scenario_id"],
                            "elapsed_seconds": time.perf_counter() - started,
                            "free_bytes": shutil.disk_usage(output_dir.parent).free,
                            "fresh_b_opened": False,
                        },
                    )
    terminal = validate_terminal_acceptance(
        results,
        snapshot_index_count=snapshot_count,
    )
    family_counts = collections.Counter(row["family"] for row in results)
    family_snapshots = collections.Counter()
    for row in results:
        family_snapshots[row["family"]] += int(row["snapshot_count"])
    if set(family_counts) != set(SCENARIO_FAMILIES):
        raise RuntimeError("controlled train family denominator drifted")
    _write_json_atomic(
        progress_path,
        {
            "schema_version": SCHEMA_VERSION,
            "status": "complete",
            "completed": len(results),
            "total": len(cases),
            "complete": sum(r["status"] == "complete" for r in results),
            "failed": sum(r["status"] == "failed" for r in results),
            "snapshot_count": snapshot_count,
            "elapsed_seconds": time.perf_counter() - started,
            "free_bytes": shutil.disk_usage(output_dir.parent).free,
            "fresh_b_opened": False,
        },
    )
    return {
        **dict(common),
        "mode": "execute",
        "status": "passed",
        "preflight_artifact": str(preflight_artifact),
        "preflight_root_sha256": preflight["root_sha256"],
        "attempted_identity_count": len(results),
        "source_ineligible_retained_identity_count": EXPECTED_RETAINED_INELIGIBLE,
        "formal_train_manifest_identity_count": (
            len(results) + EXPECTED_RETAINED_INELIGIBLE
        ),
        "complete_identity_count": terminal["complete_identity_count"],
        "failed_identity_count": sum(r["status"] == "failed" for r in results),
        "retained_capability_failure_count": terminal[
            "retained_capability_failure_count"
        ],
        "retained_identity_count": len(results),
        "snapshot_count": snapshot_count,
        "snapshot_capacity": len(cases) * CORPUS_STEPS,
        "family_identity_counts": dict(family_counts),
        "family_snapshot_counts": dict(family_snapshots),
        "failure_reason_counts": dict(
            collections.Counter(
                row["failure_reason"] for row in results if row["status"] == "failed"
            )
        ),
        "wall_seconds": time.perf_counter() - started,
        "candidate_tensors_modified": False,
        "training_snapshot_outcome_fields": [],
        "runtime_outcomes_not_read_or_copied_to_training_snapshots": True,
        "selector_training_executed": False,
        "calibration_executed": False,
        "fresh_b_opened": False,
        "claim_authorized": False,
    }


def combine_snapshot_context(
    *,
    snapshot: Mapping[str, Any],
    context: Mapping[str, Any],
    case: Mapping[str, Any],
    tick_index: int,
) -> dict[str, Any]:
    if snapshot.get("schema_version") != "v22_native_decision_snapshot_v1":
        raise ValueError("native snapshot schema mismatch")
    features = snapshot.get("feature_payload")
    sidecar = snapshot.get("sidecar")
    raw = context.get("raw_context")
    source_complete = context.get("source_complete")
    source_receipt = context.get("source_receipt")
    if (
        context.get("schema_version") != CONTEXT_SCHEMA_VERSION
        or not all(
            isinstance(value, Mapping)
            for value in (features, sidecar, raw, source_complete, source_receipt)
        )
    ):
        raise ValueError("controlled snapshot/context payload is malformed")
    atoms = np.asarray(features.get("atom_matrix"), dtype=np.float64)
    valid = features.get("source_valid_mask")
    rows = features.get("candidate_row_sha256")
    if (
        atoms.shape != (8, 14)
        or not np.isfinite(atoms).all()
        or np.any(atoms < 0.0)
        or not isinstance(valid, list)
        or len(valid) != 8
        or any(not isinstance(value, bool) for value in valid)
        or not isinstance(rows, list)
        or len(rows) != 8
        or any(not _is_sha256(value) for value in rows)
    ):
        raise ValueError("controlled snapshot atoms/masks are invalid")
    if tuple(raw) != RAW_FEATURE_NAMES or tuple(source_complete) != RAW_FEATURE_NAMES:
        raise ValueError("controlled raw-context schema drifted")
    raw_values = np.asarray([raw[name] for name in RAW_FEATURE_NAMES], dtype=np.float64)
    if not np.isfinite(raw_values).all() or any(
        not isinstance(source_complete[name], bool) for name in RAW_FEATURE_NAMES
    ):
        raise ValueError("controlled raw context is nonfinite or has invalid sources")
    timing_name = "traffic_signal_phase_remaining_s"
    if (
        float(raw[timing_name]) != 0.0
        or source_complete[timing_name] is not False
        or source_receipt.get("mode") != "no_v2i"
        or source_receipt.get("phase_remaining_available") is not False
    ):
        raise ValueError("controlled no-V2I context exposed future signal timing")
    physical = sidecar.get("physical_feasible_mask")
    sidecar_source_valid = sidecar.get("source_valid_mask")
    selected_index = sidecar.get("selected_index")
    scores = np.asarray(sidecar.get("scores"), dtype=np.float64)
    if (
        not isinstance(physical, list)
        or len(physical) != 8
        or any(not isinstance(value, bool) for value in physical)
        or not isinstance(sidecar_source_valid, list)
        or len(sidecar_source_valid) != 8
        or any(not isinstance(value, bool) for value in sidecar_source_valid)
        or sidecar_source_valid != valid
        or isinstance(selected_index, bool)
        or not isinstance(selected_index, int)
        or selected_index < 0
        or selected_index >= 8
        or scores.shape != (8,)
        or not np.isfinite(scores).all()
        or sidecar.get("score_contract")
        != "score_k=clip(a_k/s,0,10)^T w"
        or sidecar.get("tie_break_contract")
        != "lowest_eligible_candidate_index"
        or selected_index
        != int(
            np.argmin(
                np.where(np.asarray(valid, dtype=bool), scores, np.inf)
            )
        )
        or not _is_sha256(sidecar.get("normalized_atom_matrix_sha256"))
    ):
        raise ValueError("controlled selector score/mask invariant failed")
    if (
        sidecar.get("candidate_tensor_sha256_before")
        != sidecar.get("candidate_tensor_sha256_after")
        or sidecar.get("candidate0_sha256") != rows[0]
        or case.get("outcome_fields_consumed") != []
        or case.get("holdout_outcome_consumed") is not False
        or case.get("split") != "train"
    ):
        raise ValueError("controlled snapshot immutability/outcome boundary failed")
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "feature_payload": {
            "atom_matrix": atoms.tolist(),
            "source_valid_mask": list(valid),
            "candidate_row_sha256": list(rows),
            "raw_context": {name: float(raw[name]) for name in RAW_FEATURE_NAMES},
            "context_source_complete": {
                name: bool(source_complete[name]) for name in RAW_FEATURE_NAMES
            },
        },
        "sidecar": {
            "tick_index": int(tick_index),
            "scenario_id": str(case["scenario_id"]),
            "family": str(case["family"]),
            "tier": str(case["tier"]),
            "parameter_block_id": str(case["parameter_block_id"]),
            "route_identity_sha256": str(case["route_identity_sha256"]),
            "corridor_group_sha256": str(case["corridor_group_sha256"]),
            "map_family_id": str(case["map_family_id"]),
            "seed": EXPECTED_SEED,
            "candidate_tensor_sha256_before": str(
                sidecar["candidate_tensor_sha256_before"]
            ),
            "candidate_tensor_sha256_after": str(
                sidecar["candidate_tensor_sha256_after"]
            ),
            "causal_input_sha256": str(sidecar["causal_input_sha256"]),
            "physical_feasible_mask": list(physical),
            "source_valid_mask": list(sidecar_source_valid),
            "all_k_high_risk": bool(sidecar["all_k_high_risk"]),
            "selected_index": int(selected_index),
            "score_contract": str(sidecar["score_contract"]),
            "tie_break_contract": str(sidecar["tie_break_contract"]),
            "normalized_atom_matrix_sha256": str(
                sidecar["normalized_atom_matrix_sha256"]
            ),
            "context_schema_version": CONTEXT_SCHEMA_VERSION,
            "context_source_receipt": dict(source_receipt),
            "offline_label_provenance": "pending_train_only_causal_label",
            "outcome_fields_consumed": [],
            "fresh_b_opened": False,
        },
    }


def _shared_assets(config: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "fixed_dp": json.loads(json.dumps(config["fixed_dp"])),
        "selector": json.loads(json.dumps(config["selector"])),
    }


def _verify_case_assets_cached(
    config: Mapping[str, Any], *, seen_routes: set[str], seen_maps: set[str]
) -> None:
    map_asset = config["map"]
    route_asset = config["routes"][0]
    map_key = str(map_asset["sha256"])
    route_key = str(route_asset["name"])
    if map_key not in seen_maps:
        path = Path(str(map_asset["path"]))
        if not path.is_file() or _file_sha256(path) != map_key:
            raise ValueError("v25 controlled map asset SHA256 mismatch")
        seen_maps.add(map_key)
    if route_key not in seen_routes:
        path = Path(str(route_asset["path"]))
        if not path.is_file() or _file_sha256(path) != route_asset["sha256"]:
            raise ValueError("v25 controlled route asset SHA256 mismatch")
        seen_routes.add(route_key)


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    _write_json(temporary, payload)
    os.replace(temporary, path)


def _git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()


def _tracked_dirty(repo: Path) -> bool:
    return subprocess.run(
        ["git", "-C", str(repo), "diff", "--quiet", "HEAD", "--"], check=False
    ).returncode != 0


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and not (set(value) - set("0123456789abcdef"))
    )


def _lock_is_free(path: Path) -> bool:
    import fcntl

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return True


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    import fcntl

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


if __name__ == "__main__":
    main()
