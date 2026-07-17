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
    RetainedScenarioCapabilityFailure,
    SCENARIO_FAMILIES,
    ScenarioCapabilityReason,
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
PREREGISTERED_CAPABILITY_FAILURE_LIMITS = {
    (
        "red_light_phase_timing",
        ScenarioCapabilityReason.MAPPED_CURRENT_SIGNAL_SOURCE_UNAVAILABLE.value,
    ): 32,
}
RED_SCIENTIFIC_MIN_COMPLETE_BY_TIER = {
    "easy": 4,
    "borderline": 7,
    "high_risk": 4,
}
RED_SCIENTIFIC_MIN_DISTINCT_SOURCE_MAPS = 3


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
    capability_failure: Mapping[str, Any] | None = None,
    capability_allowlist: Mapping[str, Mapping[str, Any]] | None = None,
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
        if (
            failure_type is not None
            or failure_reason is not None
            or capability_failure is not None
        ):
            raise ArtifactContractViolation("complete identity carries failure metadata")
        return "complete"
    if status != "failed":
        raise ArtifactContractViolation("identity status is neither complete nor failed")
    if any(counts):
        raise ArtifactContractViolation(
            "partial snapshots are forbidden and make the artifact ineligible"
        )
    if failure_type == RetainedScenarioCapabilityFailure.__name__:
        _validate_capability_failure_receipt(
            capability_failure,
            capability_allowlist=capability_allowlist,
        )
        return "retained_capability_failure"
    raise ArtifactContractViolation(
        "only an explicit preregistered scenario-capability failure may be retained"
    )


def validate_terminal_acceptance(
    results: list[Mapping[str, Any]],
    *,
    snapshot_index_count: int,
    expected_identity_count: int = EXPECTED_EXECUTABLE_IDENTITIES,
    capability_allowlist: Mapping[str, Mapping[str, Any]] | None = None,
    expected_identity_families: Mapping[str, str] | None = None,
    expected_red_authority: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if len(results) != expected_identity_count:
        raise ArtifactContractViolation(
            "terminal identity denominator is incomplete"
        )
    complete = 0
    retained_capability = 0
    retained_by_contract: collections.Counter[tuple[str, str]] = collections.Counter()
    scenario_ids = [row.get("scenario_id") for row in results]
    if (
        any(not isinstance(value, str) or not value for value in scenario_ids)
        or len(set(scenario_ids)) != len(scenario_ids)
    ):
        raise ArtifactContractViolation(
            "terminal results require unique formal scenario identities"
        )
    if expected_identity_families is not None and {
        str(row["scenario_id"]): str(row.get("family")) for row in results
    } != dict(expected_identity_families):
        raise ArtifactContractViolation(
            "terminal scenario identity/family denominator drifted"
        )
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
            and row.get("failure_type") == RetainedScenarioCapabilityFailure.__name__
        ):
            receipt = _validate_capability_failure_receipt(
                row.get("capability_failure"),
                capability_allowlist=capability_allowlist,
            )
            if (
                receipt["scenario_id"] != row["scenario_id"]
                or receipt["family"] != row.get("family")
            ):
                raise ArtifactContractViolation(
                    "capability failure receipt does not bind the result identity"
                )
            retained_capability += 1
            contract = (receipt["family"], receipt["reason"])
            retained_by_contract[contract] += 1
            limit = PREREGISTERED_CAPABILITY_FAILURE_LIMITS.get(contract)
            if limit is None or retained_by_contract[contract] > limit:
                raise ArtifactContractViolation(
                    "retained scenario-capability failures exceed the "
                    "preregistered limit"
                )
        else:
            raise ArtifactContractViolation(
                "terminal results contain an illegal failure or partial identity"
            )
    expected_snapshots = complete * CORPUS_STEPS
    if complete == 0:
        raise ArtifactContractViolation(
            "a corpus with no complete identities cannot pass terminal acceptance"
        )
    for contract, count in retained_by_contract.items():
        limit = PREREGISTERED_CAPABILITY_FAILURE_LIMITS.get(contract)
        if limit is None or count > limit:
            raise ArtifactContractViolation(
                "retained scenario-capability failures exceed the preregistered limit"
            )
    red_coverage = None
    if expected_red_authority is not None:
        if len(expected_red_authority) != 21:
            raise ArtifactContractViolation(
                "formal red-light authority must contain exactly 21 identities"
            )
        formal_by_tier: collections.Counter[str] = collections.Counter()
        formal_maps: set[str] = set()
        for scenario_id, authority in expected_red_authority.items():
            if (
                not isinstance(scenario_id, str)
                or not isinstance(authority, Mapping)
                or authority.get("tier") not in RED_SCIENTIFIC_MIN_COMPLETE_BY_TIER
                or authority.get("mapped_traffic_light") is not True
                or not isinstance(authority.get("source_map_sha256"), str)
            ):
                raise ArtifactContractViolation(
                    "formal red-light mapping authority is invalid"
                )
            formal_by_tier[str(authority["tier"])] += 1
            formal_maps.add(str(authority["source_map_sha256"]))
        if dict(formal_by_tier) != {
            "easy": 6,
            "borderline": 10,
            "high_risk": 5,
        } or len(formal_maps) != 4:
            raise ArtifactContractViolation(
                "formal red-light capability census drifted"
            )
        complete_ids = {
            str(row["scenario_id"])
            for row in results
            if row.get("status") == "complete"
        }
        complete_by_tier: collections.Counter[str] = collections.Counter()
        complete_maps: set[str] = set()
        for scenario_id, authority in expected_red_authority.items():
            if scenario_id in complete_ids:
                complete_by_tier[str(authority["tier"])] += 1
                complete_maps.add(str(authority["source_map_sha256"]))
        tier_pass = all(
            complete_by_tier[tier] >= minimum
            for tier, minimum in RED_SCIENTIFIC_MIN_COMPLETE_BY_TIER.items()
        )
        maps_pass = len(complete_maps) >= RED_SCIENTIFIC_MIN_DISTINCT_SOURCE_MAPS
        red_coverage = {
            "formal_identity_count": len(expected_red_authority),
            "formal_by_tier": dict(formal_by_tier),
            "formal_distinct_source_map_count": len(formal_maps),
            "complete_by_tier": {
                tier: int(complete_by_tier[tier])
                for tier in RED_SCIENTIFIC_MIN_COMPLETE_BY_TIER
            },
            "complete_distinct_source_map_count": len(complete_maps),
            "minimum_complete_by_tier": dict(
                RED_SCIENTIFIC_MIN_COMPLETE_BY_TIER
            ),
            "minimum_distinct_source_maps": (
                RED_SCIENTIFIC_MIN_DISTINCT_SOURCE_MAPS
            ),
            "passed": bool(tier_pass and maps_pass),
        }
        if not red_coverage["passed"]:
            raise ArtifactContractViolation(
                "red-light capability coverage is scientifically ineligible"
            )
    if snapshot_index_count != expected_snapshots:
        raise ArtifactContractViolation(
            "terminal snapshot index does not match complete identities"
        )
    summary: dict[str, Any] = {
        "complete_identity_count": complete,
        "retained_capability_failure_count": retained_capability,
        "training_snapshot_count": expected_snapshots,
    }
    if red_coverage is not None:
        summary["red_scientific_coverage"] = red_coverage
    return summary


def build_capability_failure_allowlist(
    cases: list[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Bind retainable capability failures to formal identities and families."""
    allowed_reason = (
        ScenarioCapabilityReason.MAPPED_CURRENT_SIGNAL_SOURCE_UNAVAILABLE.value
    )
    return {
        str(case["scenario_id"]): {
            "family": "red_light_phase_timing",
            "reasons": [allowed_reason],
        }
        for case in cases
        if case.get("family") == "red_light_phase_timing"
        and case.get("runner_eligible") is True
    }


def _validate_capability_failure_receipt(
    receipt: Mapping[str, Any] | None,
    *,
    capability_allowlist: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, str]:
    if not isinstance(receipt, Mapping) or set(receipt) != {
        "scenario_id",
        "family",
        "reason",
    }:
        raise ArtifactContractViolation(
            "retained capability failure requires an exact structured receipt"
        )
    if not isinstance(capability_allowlist, Mapping):
        raise ArtifactContractViolation("capability failure allowlist is unavailable")
    normalized = {name: str(receipt[name]) for name in receipt}
    authority = capability_allowlist.get(normalized["scenario_id"])
    if (
        not isinstance(authority, Mapping)
        or authority.get("family") != normalized["family"]
        or normalized["reason"] not in authority.get("reasons", [])
    ):
        raise ArtifactContractViolation(
            "capability failure is not in the formal identity/family/reason allowlist"
        )
    try:
        ScenarioCapabilityReason(normalized["reason"])
    except ValueError as exc:
        raise ArtifactContractViolation(
            "capability failure reason is not a registered enum value"
        ) from exc
    return normalized


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
        "released_camp_source_head": camp_head,
        "current_repo_head_at_run": camp_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "formal_artifact": str(FORMAL_ARTIFACT),
        "formal_root_sha256": formal_receipt,
        "probe_template": str(args.probe_template),
        "probe_template_sha256": EXPECTED_TEMPLATE_SHA256,
        "generation_scales": {
            "path": str(CORRECTED_GENERATION_SCALES),
            "sha256": _file_sha256(CORRECTED_GENERATION_SCALES),
        },
        "static_weights": dict(template["selector"]["weights"]),
        "seed": EXPECTED_SEED,
        "corpus_steps": CORPUS_STEPS,
        "snapshot_capacity": len(cases) * CORPUS_STEPS,
        "train_lock": str(TRAIN_LOCK),
        "minimum_free_bytes": MINIMUM_FREE_BYTES,
        "rejected_roots": [SUPERSEDED_PARTIAL_CORPUS_ROOT],
        "terminal_lock_scope": "execution_through_progress_report_run_exit_and_seal",
        "free_bytes_at_start": shutil.disk_usage(args.output_dir.parent).free,
        "fresh_b_opened": False,
        "outcome_fields_consumed": [],
    }
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
        report = _preflight(cases, template, route_assets, common)
        _write_json(args.output_dir / "source_receipt.json", report)
        return report
    if args.preflight_artifact is None:
        raise ValueError("execution requires --preflight-artifact")
    expected_config_receipts = _config_authority_receipts(
        cases, template, route_assets
    )
    preflight = _verify_preflight(
        args.preflight_artifact,
        camp_head,
        expected_config_root_sha256=_canonical_sha256(expected_config_receipts),
    )
    common = {
        **common,
        "config_receipts_root_sha256": _canonical_sha256(
            expected_config_receipts
        ),
    }
    _write_json(args.output_dir / "source_receipt.json", common)
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
        authority = _config_authority_receipt(config)
        receipts.append(
            {
                **authority,
                "config_authority_sha256": _canonical_sha256(authority),
            }
        )
    config_root = _canonical_sha256(receipts)
    return {
        **dict(common),
        "static_weights": dict(shared["selector"]["weights"]),
        "config_receipts_root_sha256": config_root,
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


def _config_authority_receipts(
    cases: list[Mapping[str, Any]],
    template: Mapping[str, Any],
    route_assets: Mapping[str, Mapping[str, str]],
) -> list[dict[str, Any]]:
    receipts = []
    for case in cases:
        identity = str(case["route_identity_sha256"])
        authority = _config_authority_receipt(
            build_controlled_train_config(
                template,
                case,
                route_assets[identity],
            )
        )
        receipts.append(
            {
                **authority,
                "config_authority_sha256": _canonical_sha256(authority),
            }
        )
    return receipts


def _config_authority_receipt(config: Mapping[str, Any]) -> dict[str, Any]:
    controlled = config["controlled_scenario"]
    protocol = config["protocol"]
    selector = config["selector"]
    fixed_dp = config["fixed_dp"]
    route = config["routes"][0]
    return {
        "schema_version": str(config["schema_version"]),
        "scenario_id": str(controlled["scenario_id"]),
        "family": str(controlled["family"]),
        "tier": str(controlled["tier"]),
        "route_identity_sha256": str(controlled["route_identity_sha256"]),
        "map_sha256": str(config["map"]["sha256"]),
        "route_sha256": str(route["sha256"]),
        "fixed_dp_head": str(fixed_dp["head"]),
        "fixed_dp_checkpoint_sha256": str(fixed_dp["checkpoint"]["sha256"]),
        "fixed_dp_args_sha256": str(fixed_dp["args_json"]["sha256"]),
        "generation_scales_sha256": str(selector["atom_scales"]["sha256"]),
        "static_weights_sha256": str(selector["weights"]["sha256"]),
        "selector_role": str(selector["role"]),
        "seed": int(config["seeds"]["scenario"]),
        "corpus_steps": int(protocol["corpus_steps"]),
        "context_schema_version": str(protocol["context_schema_version"]),
        "context_mode": str(protocol["context_mode"]),
        "selector_training_execution_authorized": bool(
            protocol["selector_training_execution_authorized"]
        ),
        "calibration_authorized": bool(protocol["calibration_authorized"]),
        "holdout_access_authorized": bool(
            protocol["holdout_access_authorized"]
        ),
        "fresh_b_opened": bool(protocol["fresh_b_opened"]),
        "outcome_fields_consumed": list(
            controlled["outcome_fields_consumed"]
        ),
    }


def _asset_receipt_matches(payload: Any) -> bool:
    if not isinstance(payload, Mapping) or set(payload) != {"path", "sha256"}:
        return False
    path = Path(str(payload["path"]))
    return path.is_file() and _file_sha256(path) == payload["sha256"]


def _verify_preflight(
    path: Path,
    camp_head: str,
    *,
    expected_config_root_sha256: str,
) -> dict[str, Any]:
    root = _verify_seal(path)
    report = _load_json(path / "report.json")
    source_receipt = _load_json(path / "source_receipt.json")
    run_exit = (path / "run.exit").read_text(encoding="ascii")
    heads = (path / "HEADS").read_text(encoding="ascii").splitlines()
    command = (path / "COMMAND").read_text(encoding="utf-8").strip()
    receipts = report.get("config_receipts")
    required_keys = {
        "schema_version",
        "status",
        "mode",
        "camp_head",
        "released_camp_source_head",
        "current_repo_head_at_run",
        "fixed_dp_head",
        "formal_artifact",
        "formal_root_sha256",
        "probe_template",
        "probe_template_sha256",
        "generation_scales",
        "static_weights",
        "config_receipts_root_sha256",
        "seed",
        "corpus_steps",
        "snapshot_capacity",
        "validated_identity_count",
        "training_executed",
        "calibration_executed",
        "fresh_b_opened",
        "outcome_fields_consumed",
        "config_receipts",
        "rejected_roots",
    }
    if (
        not required_keys.issubset(report)
        or report.get("status") != "passed"
        or report.get("mode") != "preflight"
        or report.get("schema_version") != SCHEMA_VERSION
        or report.get("camp_head") != camp_head
        or report.get("released_camp_source_head") != camp_head
        or report.get("current_repo_head_at_run") != camp_head
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("formal_artifact") != str(FORMAL_ARTIFACT)
        or report.get("formal_root_sha256") != FORMAL_ROOT_SHA256
        or report.get("probe_template_sha256") != EXPECTED_TEMPLATE_SHA256
        or report.get("generation_scales")
        != {
            "path": str(CORRECTED_GENERATION_SCALES),
            "sha256": _file_sha256(CORRECTED_GENERATION_SCALES),
        }
        or not _asset_receipt_matches(report.get("static_weights"))
        or not isinstance(receipts, list)
        or len(receipts) != EXPECTED_EXECUTABLE_IDENTITIES
        or len(
            {
                receipt.get("scenario_id")
                for receipt in receipts
                if isinstance(receipt, Mapping)
            }
        )
        != EXPECTED_EXECUTABLE_IDENTITIES
        or report.get("config_receipts_root_sha256")
        != _canonical_sha256(receipts)
        or report.get("config_receipts_root_sha256")
        != expected_config_root_sha256
        or any(
            not isinstance(receipt, Mapping)
            or receipt.get("config_authority_sha256")
            != _canonical_sha256(
                {
                    key: value
                    for key, value in receipt.items()
                    if key != "config_authority_sha256"
                }
            )
            for receipt in (receipts if isinstance(receipts, list) else [])
        )
        or report.get("seed") != EXPECTED_SEED
        or report.get("corpus_steps") != CORPUS_STEPS
        or report.get("snapshot_capacity")
        != EXPECTED_EXECUTABLE_IDENTITIES * CORPUS_STEPS
        or report.get("validated_identity_count") != EXPECTED_EXECUTABLE_IDENTITIES
        or report.get("training_executed") is not False
        or report.get("calibration_executed") is not False
        or report.get("fresh_b_opened") is not False
        or report.get("outcome_fields_consumed") != []
        or report.get("rejected_roots") != [SUPERSEDED_PARTIAL_CORPUS_ROOT]
        or source_receipt != report
        or run_exit != "0\n"
        or not command
        or heads
        != [f"camp_source_head={camp_head}", f"fixed_dp_head={FIXED_DP_HEAD}"]
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
    capability_allowlist = build_capability_failure_allowlist(cases)
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
                    capability_failure = None
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
                    except RetainedScenarioCapabilityFailure as exc:
                        status = "failed"
                        failure_type = type(exc).__name__
                        failure_reason = str(exc)
                        capability_failure = exc.as_receipt()
                    disposition = validate_identity_terminal(
                        status=status,
                        receipt_tick_count=receipt_tick_count,
                        snapshot_count=len(snapshots),
                        context_count=len(contexts),
                        failure_type=failure_type,
                        failure_reason=failure_reason,
                        capability_failure=capability_failure,
                        capability_allowlist=capability_allowlist,
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
                        "capability_failure": capability_failure,
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
        capability_allowlist=capability_allowlist,
        expected_identity_families={
            str(case["scenario_id"]): str(case["family"]) for case in cases
        },
        expected_red_authority={
            str(case["scenario_id"]): {
                "tier": str(case["tier"]),
                "source_map_sha256": str(case["source_map_sha256"]),
                "mapped_traffic_light": case.get("source_availability", {}).get(
                    "mapped_traffic_light"
                ),
            }
            for case in cases
            if case.get("family") == "red_light_phase_timing"
        },
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
        "red_scientific_coverage": terminal["red_scientific_coverage"],
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
    default_output_sha256 = sidecar.get("default_output_sha256")
    candidate0_sha256 = sidecar.get("candidate0_sha256")
    default_candidate0_identity = sidecar.get("default_candidate0_identity")
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
        or not isinstance(default_candidate0_identity, Mapping)
        or default_output_sha256 != rows[0]
        or candidate0_sha256 != rows[0]
        or default_candidate0_identity.get("elementwise_equal") is not True
        or default_candidate0_identity.get("default_output_sha256") != rows[0]
        or default_candidate0_identity.get("candidate0_sha256") != rows[0]
        or default_candidate0_identity.get("native_ranked_k8") is not False
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
            "default_output_sha256": str(default_output_sha256),
            "candidate0_sha256": str(candidate0_sha256),
            "default_candidate0_identity": dict(default_candidate0_identity),
            "candidate0_semantics": (
                "operational_default_alias_from_same_forward"
            ),
            "candidate0_independent_second_forward": False,
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


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _canonical_sha256(payload: Any) -> str:
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
