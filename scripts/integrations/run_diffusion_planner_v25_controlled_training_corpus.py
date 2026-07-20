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
from camp_core.integrations.diffusion_planner import (  # noqa: E402
    install_lanelet2_projection_fallback,
    require_source_preserving_lanelet2_regulatory_adapter,
)
from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_causal_atoms import (  # noqa: E402
    FixedDpCandidateGenerationCapabilityFailure,
    compute_authorized_red_stopping_margin_costs,
    validate_fixed_k8_candidate_tensor,
)
from camp_core.integrations.diffusion_planner_v25_a162_bounded_execution import (  # noqa: E402
    FIXED_DP_FAILURE_CLASS,
    FIXED_DP_FAILURE_RECEIPT_SCHEMA_VERSION,
)
from camp_core.integrations.diffusion_planner_v25_a17_full_corpus_authority import (  # noqa: E402
    EXECUTE_RELEASE_SCHEMA_VERSION as A17_EXECUTE_RELEASE_SCHEMA_VERSION,
    NONCE_LEDGER as A17_FULL_CORPUS_NONCE_LEDGER,
    PREFLIGHT_GATE as A17_FULL_CONFIG_PREFLIGHT_GATE,
    PREFLIGHT_RELEASE_SCHEMA_VERSION as A17_PREFLIGHT_RELEASE_SCHEMA_VERSION,
    UPSTREAM_ROLES as A17_UPSTREAM_ROLES,
    verify_release as verify_a17_full_corpus_release,
)
from camp_core.integrations.diffusion_planner_v25_causal_evidence_store import (  # noqa: E402
    externalize_causal_evidence,
)
from camp_core.integrations.diffusion_planner_v25_snapshot_store import (  # noqa: E402
    SNAPSHOT_SUFFIX,
    encode_snapshot,
)
from camp_core.integrations.diffusion_planner_v25_full_r_authority import (  # noqa: E402
    CANONICAL_JSON_BYTE_SPEC_VERSION,
    EXECUTE_RELEASE_SCHEMA_VERSION,
    PREFLIGHT_RELEASE_SCHEMA_VERSION,
    ROOT_ROLES,
    build_critical_implementation_manifest,
    canonical_json_bytes,
    consume_one_shot_nonce,
    verify_dual_head_contract,
    verify_seven_root_chain,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (  # noqa: E402
    NO_SIGNAL_CHAIN_SCHEMA_VERSION,
    build_semantic_clone_payload,
    canonical_json_sha256,
    validate_causal_signal_atom_input,
    validate_no_signal_chain,
    validate_runtime_no_signal_receipt,
)
from camp_core.integrations.diffusion_planner_v25_route_signal_authority import (  # noqa: E402
    validate_mapped_signal_causal_atom_input,
    validate_mapped_signal_chain,
    validate_mapped_signal_runtime_receipt,
)
from camp_core.integrations.diffusion_planner_v25_controlled_scenarios import (  # noqa: E402
    MODEL_INPUT_SIGNAL_CACHE_RECEIPT_SCHEMA_VERSION,
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


SCHEMA_VERSION = "camp_dp_v25_controlled_training_corpus_execution_v8"
SNAPSHOT_SCHEMA_VERSION = "camp_dp_v25_controlled_train_snapshot_v9"
SEMANTIC_AUTHORITY_SIDECAR_SCHEMA_VERSION = (
    "camp_dp_v25_full_r_semantic_authority_chains_v3"
)
ROUTE_SIGNAL_SOURCE_RECEIPTS_SCHEMA_VERSION = (
    "camp_dp_v25_a161_route_signal_source_receipts_v2"
)
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
RELEASE_NONCE_LEDGER = Path(
    "/root/autodl-tmp/.camp_dp_v25_controlled_train_release_nonces"
)
S01_NATIVE_SOURCE_ROOTS = {
    "s01_preflight": "bba8f0581efa688a4a85f193eed966f38501ac96de4883c493ab81caa1760451",
    "s01_review": "facfe0a1f4458e52ea2235197e7a2949537a1021c0d6fa69d5cf0018732f392d",
}
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
        "mapped_signal",
        ScenarioCapabilityReason.MAPPED_CURRENT_SIGNAL_SOURCE_UNAVAILABLE.value,
    ): 146,
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
    if failure_type == FixedDpCandidateGenerationCapabilityFailure.__name__:
        _validate_fixed_dp_capability_failure_receipt(capability_failure)
        return "retained_fixed_dp_capability_failure"
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
    expected_support_authority: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if len(results) != expected_identity_count:
        raise ArtifactContractViolation(
            "terminal identity denominator is incomplete"
        )
    complete = 0
    retained_capability = 0
    retained_fixed_dp = 0
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
            contract = (receipt["source_class"], receipt["reason"])
            retained_by_contract[contract] += 1
            limit = PREREGISTERED_CAPABILITY_FAILURE_LIMITS.get(contract)
            if limit is None or retained_by_contract[contract] > limit:
                raise ArtifactContractViolation(
                    "retained scenario-capability failures exceed the "
                    "preregistered limit"
                )
        elif (
            status == "failed"
            and snapshot_count == 0
            and row.get("failure_type")
            == FixedDpCandidateGenerationCapabilityFailure.__name__
        ):
            receipt = _validate_fixed_dp_capability_failure_receipt(
                row.get("capability_failure")
            )
            if (
                receipt["scenario_id"] != row["scenario_id"]
                or receipt["family"] != row.get("family")
                or receipt["tier"] != row.get("tier")
                or receipt["route_identity_sha256"]
                != row.get("route_identity_sha256")
            ):
                raise ArtifactContractViolation(
                    "fixed-DP capability receipt does not bind result identity"
                )
            retained_fixed_dp += 1
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
    support_coverage = None
    if expected_support_authority is not None:
        support_coverage = _full_support_coverage(
            results=results,
            authority=expected_support_authority,
        )
        if support_coverage["passed"] is not True:
            raise ArtifactContractViolation(
                "full corpus fixed-DP support coverage gate failed"
            )
    summary: dict[str, Any] = {
        "complete_identity_count": complete,
        "retained_capability_failure_count": (
            retained_capability + retained_fixed_dp
        ),
        "retained_scenario_capability_failure_count": retained_capability,
        "retained_fixed_dp_capability_failure_count": retained_fixed_dp,
        "training_snapshot_count": expected_snapshots,
    }
    if red_coverage is not None:
        summary["red_scientific_coverage"] = red_coverage
    if support_coverage is not None:
        summary["fixed_dp_support_coverage"] = support_coverage
    return summary


def build_capability_failure_allowlist(
    cases: list[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Bind retainable failures to formal route-source state, not family."""
    allowed_reason = (
        ScenarioCapabilityReason.MAPPED_CURRENT_SIGNAL_SOURCE_UNAVAILABLE.value
    )
    return {
        str(case["scenario_id"]): {
            "family": str(case["family"]),
            "source_class": "mapped_signal",
            "phase_authority_mode": str(case["phase_authority_mode"]),
            "reasons": [allowed_reason],
        }
        for case in cases
        if case.get("signal_source_class") == "mapped_signal"
        and case.get("phase_authority_mode")
        in {"controlled_same_tick_override", "observe_same_tick_request"}
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
        "source_class",
        "phase_authority_mode",
        "reason",
    }:
        raise ArtifactContractViolation(
            "retained capability failure requires an exact structured receipt"
        )
    if not isinstance(capability_allowlist, Mapping):
        raise ArtifactContractViolation("capability failure allowlist is unavailable")
    if any(type(receipt[name]) is not str or not receipt[name] for name in receipt):
        raise ArtifactContractViolation(
            "retained capability failure receipt values must be native strings"
        )
    normalized = dict(receipt)
    authority = capability_allowlist.get(normalized["scenario_id"])
    if (
        not isinstance(authority, Mapping)
        or authority.get("family") != normalized["family"]
        or authority.get("source_class") != normalized["source_class"]
        or authority.get("phase_authority_mode")
        != normalized["phase_authority_mode"]
        or normalized["reason"] not in authority.get("reasons", [])
    ):
        raise ArtifactContractViolation(
            "capability failure is not in the formal route-source-state allowlist"
        )
    try:
        ScenarioCapabilityReason(normalized["reason"])
    except ValueError as exc:
        raise ArtifactContractViolation(
            "capability failure reason is not a registered enum value"
        ) from exc
    return normalized


def _validate_fixed_dp_capability_failure_receipt(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    fields = {
        "schema_version", "failure_class", "reason", "scenario_id",
        "route_identity_sha256", "family", "tier", "source_class",
        "phase_authority_mode", "source_map_sha256", "corridor_group_sha256",
        "fixed_dp_head", "tick_index", "invalid_indices", "invalid_count",
        "minimum_heading_norm", "maximum_heading_norm",
        "heading_norm_minimum", "heading_norm_maximum", "raw_k8_sha256",
        "candidate0_sha256", "default_output_sha256",
        "default_candidate0_identity", "raw_preimage", "training_eligible",
        "calibration_eligible", "evaluation_eligible", "fresh_b2_opened",
        "outcome_fields_consumed",
    }
    if type(value) is not dict or set(value) != fields:
        raise ArtifactContractViolation(
            "fixed-DP capability failure receipt schema drifted"
        )
    if (
        value.get("schema_version") != FIXED_DP_FAILURE_RECEIPT_SCHEMA_VERSION
        or value.get("failure_class") != FIXED_DP_FAILURE_CLASS
        or value.get("reason") != "invalid_k8_heading_norm_envelope"
        or value.get("fixed_dp_head") != FIXED_DP_HEAD
        or value.get("training_eligible") is not False
        or value.get("calibration_eligible") is not False
        or value.get("evaluation_eligible") is not False
        or value.get("fresh_b2_opened") is not False
        or value.get("outcome_fields_consumed") != []
    ):
        raise ArtifactContractViolation(
            "fixed-DP capability failure contract drifted"
        )
    sha_fields = (
        "scenario_id", "route_identity_sha256", "source_map_sha256",
        "corridor_group_sha256", "raw_k8_sha256", "candidate0_sha256",
        "default_output_sha256",
    )
    if any(not _is_sha256(value.get(field)) for field in sha_fields):
        raise ArtifactContractViolation(
            "fixed-DP capability failure SHA authority drifted"
        )
    if (
        type(value.get("tick_index")) is not int
        or not 0 <= value["tick_index"] < CORPUS_STEPS
        or type(value.get("invalid_count")) is not int
        or value["invalid_count"] <= 0
        or type(value.get("invalid_indices")) is not list
        or len(value["invalid_indices"]) != value["invalid_count"]
    ):
        raise ArtifactContractViolation(
            "fixed-DP capability failure index authority drifted"
        )
    pairs = []
    for row in value["invalid_indices"]:
        if (
            type(row) is not dict
            or set(row) != {"candidate_index", "step_index"}
            or type(row.get("candidate_index")) is not int
            or type(row.get("step_index")) is not int
            or not 0 <= row["candidate_index"] < 8
            or not 0 <= row["step_index"] < 80
        ):
            raise ArtifactContractViolation(
                "fixed-DP capability failure invalid-index schema drifted"
            )
        pairs.append((row["candidate_index"], row["step_index"]))
    if pairs != sorted(set(pairs)):
        raise ArtifactContractViolation(
            "fixed-DP capability invalid indices are not unique/sorted"
        )
    numeric = (
        "minimum_heading_norm", "maximum_heading_norm",
        "heading_norm_minimum", "heading_norm_maximum",
    )
    if any(
        type(value.get(field)) not in (int, float)
        or not np.isfinite(float(value[field]))
        for field in numeric
    ) or (
        float(value["heading_norm_minimum"]) != 0.5
        or float(value["heading_norm_maximum"]) != 1.5
        or (
            float(value["minimum_heading_norm"]) >= 0.5
            and float(value["maximum_heading_norm"]) <= 1.5
        )
    ):
        raise ArtifactContractViolation(
            "fixed-DP capability heading envelope authority drifted"
        )
    preimage = value.get("raw_preimage")
    if (
        type(preimage) is not dict
        or set(preimage)
        != {"relative_path", "file_sha256", "array_sha256", "shape", "dtype"}
        or preimage.get("relative_path")
        != f"fixed_dp_capability_failures/{value['raw_k8_sha256']}.bin"
        or preimage.get("file_sha256") != value["raw_k8_sha256"]
        or preimage.get("array_sha256") != value["raw_k8_sha256"]
        or preimage.get("shape") != [8, 80, 4]
        or preimage.get("dtype") != "float32"
    ):
        raise ArtifactContractViolation(
            "fixed-DP capability raw preimage authority drifted"
        )
    identity = value.get("default_candidate0_identity")
    if (
        type(identity) is not dict
        or set(identity)
        != {
            "elementwise_equal", "max_abs_difference", "default_output_sha256",
            "candidate0_sha256", "native_ranked_k8",
        }
        or identity.get("elementwise_equal") is not True
        or identity.get("max_abs_difference") != 0.0
        or identity.get("native_ranked_k8") is not False
        or identity.get("candidate0_sha256") != value["candidate0_sha256"]
        or identity.get("default_output_sha256")
        != value["default_output_sha256"]
        or value["candidate0_sha256"] != value["default_output_sha256"]
    ):
        raise ArtifactContractViolation(
            "fixed-DP capability candidate0 same-forward authority drifted"
        )
    return dict(value)


def _full_support_coverage(
    *,
    results: list[Mapping[str, Any]],
    authority: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if set(authority) != {str(row.get("scenario_id")) for row in results}:
        raise ArtifactContractViolation("full support authority denominator drifted")
    rows = []
    for result in results:
        expected = authority[str(result["scenario_id"])]
        if any(
            result.get(field) != expected.get(field)
            for field in ("family", "tier", "route_identity_sha256")
        ):
            raise ArtifactContractViolation("full support result authority drifted")
        rows.append({**expected, "status": result["status"]})

    def grouped(fields: tuple[str, ...], minimum: int) -> dict[str, Any]:
        totals: collections.Counter[tuple[str, ...]] = collections.Counter()
        completes: collections.Counter[tuple[str, ...]] = collections.Counter()
        for row in rows:
            key = tuple(str(row[field]) for field in fields)
            totals[key] += 1
            if row["status"] == "complete":
                completes[key] += 1
        table = []
        passed = True
        for key in sorted(totals):
            ok = completes[key] > 0 and completes[key] * 100 > totals[key] * minimum
            passed = passed and ok
            table.append({"key": list(key), "planned": totals[key], "complete": completes[key], "passed": ok})
        return {"fields": list(fields), "minimum_percent_exclusive": minimum, "rows": table, "passed": passed}

    complete = sum(row["status"] == "complete" for row in rows)
    family = grouped(("family",), 90)
    source = grouped(("source_class", "phase_authority_mode"), 90)
    family_tier = grouped(("family", "tier"), 80)
    passed = bool(
        len(rows) == EXPECTED_EXECUTABLE_IDENTITIES
        and complete >= 1425
        and family["passed"]
        and source["passed"]
        and family_tier["passed"]
    )
    return {
        "planned_identity_count": len(rows),
        "complete_identity_count": complete,
        "minimum_complete_identity_count": 1425,
        "family": family,
        "source_mode": source,
        "family_tier": family_tier,
        "passed": passed,
    }


def _write_fixed_dp_capability_failure(
    *, output_dir: Path, case: Mapping[str, Any], failure: FixedDpCandidateGenerationCapabilityFailure
) -> dict[str, Any]:
    metadata = failure.canonical_metadata()
    tensor = failure.candidate_tensor_copy()
    raw = np.ascontiguousarray(tensor).tobytes(order="C")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != metadata["raw_k8_sha256"]:
        raise ArtifactContractViolation("fixed-DP capability raw digest drifted")
    relative = Path("fixed_dp_capability_failures") / f"{digest}.bin"
    path = output_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != raw:
        raise ArtifactContractViolation("fixed-DP capability raw collision")
    if not path.exists():
        path.write_bytes(raw)
    return {
        "schema_version": FIXED_DP_FAILURE_RECEIPT_SCHEMA_VERSION,
        "failure_class": metadata["failure_class"],
        "reason": metadata["reason"],
        "scenario_id": str(case["scenario_id"]),
        "route_identity_sha256": str(case["route_identity_sha256"]),
        "family": str(case["family"]),
        "tier": str(case["tier"]),
        "source_class": str(case["signal_source_class"]),
        "phase_authority_mode": case["phase_authority_mode"],
        "source_map_sha256": str(case["source_map_sha256"]),
        "corridor_group_sha256": str(case["corridor_group_sha256"]),
        "fixed_dp_head": FIXED_DP_HEAD,
        "tick_index": metadata["tick_index"],
        "invalid_indices": metadata["invalid_indices"],
        "invalid_count": metadata["invalid_count"],
        "minimum_heading_norm": metadata["minimum_heading_norm"],
        "maximum_heading_norm": metadata["maximum_heading_norm"],
        "heading_norm_minimum": metadata["heading_norm_minimum"],
        "heading_norm_maximum": metadata["heading_norm_maximum"],
        "raw_k8_sha256": digest,
        "candidate0_sha256": metadata["candidate0_sha256"],
        "default_output_sha256": metadata["default_output_sha256"],
        "default_candidate0_identity": metadata["default_candidate0_identity"],
        "raw_preimage": {"relative_path": relative.as_posix(), "file_sha256": digest, "array_sha256": digest, "shape": [8, 80, 4], "dtype": "float32"},
        "training_eligible": False,
        "calibration_eligible": False,
        "evaluation_eligible": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--preflight-artifact", type=Path)
    parser.add_argument("--r0-review-artifact", type=Path)
    parser.add_argument("--r0-review-root-sha256")
    parser.add_argument("--r0-source-artifact", type=Path)
    parser.add_argument("--r0-source-root-sha256")
    parser.add_argument("--ultra-full-config-preflight-release-artifact", type=Path)
    parser.add_argument("--ultra-full-config-preflight-release-root-sha256")
    parser.add_argument("--preflight-review-artifact", type=Path)
    parser.add_argument("--preflight-review-root-sha256")
    parser.add_argument("--ultra-full-r-execute-release-artifact", type=Path)
    parser.add_argument("--ultra-full-r-execute-release-root-sha256")
    parser.add_argument("--a17-full-corpus-release-artifact", type=Path)
    parser.add_argument("--a17-full-corpus-release-root-sha256")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    # Preflight and execute share the same lock.  It is acquired before the
    # output directory exists and remains held through report/run.exit/seal.
    with _exclusive_lock(TRAIN_LOCK):
        if args.output_dir.exists():
            raise FileExistsError(f"output already exists: {args.output_dir}")
        try:
            report = _run(args)
            args.output_dir.mkdir(parents=True, exist_ok=True)
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
            args.output_dir.mkdir(parents=True, exist_ok=True)
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
    full_r_authority = _verify_full_r_authority(
        r0_review_artifact=args.r0_review_artifact,
        r0_review_root_sha256=args.r0_review_root_sha256,
        r0_source_artifact=args.r0_source_artifact,
        r0_source_root_sha256=args.r0_source_root_sha256,
        preflight_release_artifact=(
            args.ultra_full_config_preflight_release_artifact
        ),
        preflight_release_root_sha256=(
            args.ultra_full_config_preflight_release_root_sha256
        ),
        preflight_artifact=args.preflight_artifact,
        preflight_review_artifact=args.preflight_review_artifact,
        preflight_review_root_sha256=args.preflight_review_root_sha256,
        execute_release_artifact=args.ultra_full_r_execute_release_artifact,
        execute_release_root_sha256=(
            args.ultra_full_r_execute_release_root_sha256
        ),
        a17_release_artifact=args.a17_full_corpus_release_artifact,
        a17_release_root_sha256=args.a17_full_corpus_release_root_sha256,
        camp_head=camp_head,
        mode="preflight" if args.preflight else "execute",
        output_dir=args.output_dir,
        probe_template=args.probe_template,
        dp_repo=args.dp_repo,
    )
    if _file_sha256(args.probe_template) != EXPECTED_TEMPLATE_SHA256:
        raise ValueError("probe template SHA256 mismatch")
    template = _load_json(args.probe_template)
    cases = [case for case in plan["train"] if case["runner_eligible"]]
    cases = _attach_semantic_clone_authority(
        cases,
        dp_repo=args.dp_repo,
        r0_source_artifact=Path(full_r_authority["r0_source_artifact"]),
        expected_camp_source_head=str(
            full_r_authority.get(
                "route_source_producer_head",
                full_r_authority["implementation_source_head"],
            )
        ),
        r0_source_root_sha256=str(full_r_authority["r0_source_root_sha256"]),
    )
    semantic_authority_receipts = [
        {
            "scenario_id": str(case["scenario_id"]),
            "semantic_clone_sha256": str(
                case["canonical_semantic_clone_sha256"]
            ),
            "source_chain_sha256": (
                str(
                    (
                        case.get("mapped_signal_authority")
                        or case.get("no_signal_authority")
                    )["source_chain_sha256"]
                )
            ),
        }
        for case in cases
    ]
    semantic_authority_root = _canonical_sha256(semantic_authority_receipts)
    semantic_authority_chains = [
        dict(case.get("mapped_signal_authority") or case["no_signal_authority"])
        for case in cases
    ]
    semantic_chain_root = _canonical_sha256(semantic_authority_chains)
    args.output_dir.mkdir(parents=True)
    _write_json(
        args.output_dir / "semantic_authority_chains.json",
        {
            "schema_version": SEMANTIC_AUTHORITY_SIDECAR_SCHEMA_VERSION,
            "identity_count": len(semantic_authority_chains),
            "chains_root_sha256": semantic_chain_root,
            "chains": semantic_authority_chains,
        },
    )
    route_assets = _materialize_routes(
        cases, args.output_dir / "routes", args.dp_repo
    )
    common = {
        "schema_version": SCHEMA_VERSION,
        "canonical_json_byte_spec": CANONICAL_JSON_BYTE_SPEC_VERSION,
        "camp_head": camp_head,
        "implementation_source_head": full_r_authority[
            "implementation_source_head"
        ],
        "released_camp_source_head": full_r_authority[
            "implementation_source_head"
        ],
        "current_repo_head_at_run": camp_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "dp_repo": str(args.dp_repo.resolve()),
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
        "r0_review_artifact": full_r_authority["r0_review_artifact"],
        "r0_review_root_sha256": full_r_authority["r0_review_root_sha256"],
        "r0_source_artifact": full_r_authority["r0_source_artifact"],
        "r0_source_root_sha256": full_r_authority["r0_source_root_sha256"],
        "seven_root_bindings": full_r_authority["seven_root_bindings"],
        "seven_root_bindings_sha256": full_r_authority[
            "seven_root_bindings_sha256"
        ],
        "release_run_nonce": full_r_authority["release_run_nonce"],
        "release_nonce_consumption_marker": full_r_authority[
            "release_nonce_consumption_marker"
        ],
        "authorized_output_dir": full_r_authority["authorized_output_dir"],
        "critical_implementation_manifest": full_r_authority[
            "critical_implementation_manifest"
        ],
        "ultra_full_config_preflight_release_artifact": full_r_authority[
            "preflight_release_artifact"
        ],
        "ultra_full_config_preflight_release_root_sha256": full_r_authority[
            "preflight_release_root_sha256"
        ],
        "semantic_authority_root_sha256": semantic_authority_root,
        "semantic_authority_identity_count": len(semantic_authority_receipts),
        "semantic_authority_chains_root_sha256": semantic_chain_root,
        "terminal_lock_scope": (
            "preflight_or_execution_from_before_output_creation_through_"
            "progress_report_run_exit_and_seal"
        ),
        "free_bytes_at_start": shutil.disk_usage(args.output_dir.parent).free,
        "fresh_b_opened": False,
        "outcome_fields_consumed": [],
    }
    if args.execute:
        common.update(
            {
                "preflight_review_artifact": full_r_authority[
                    "preflight_review_artifact"
                ],
                "preflight_review_root_sha256": full_r_authority[
                    "preflight_review_root_sha256"
                ],
                "ultra_full_r_execute_release_artifact": full_r_authority[
                    "execute_release_artifact"
                ],
                "ultra_full_r_execute_release_root_sha256": full_r_authority[
                    "execute_release_root_sha256"
                ],
            }
        )
    (args.output_dir / "HEADS").write_text(
        (
            f"camp_source_head={full_r_authority['implementation_source_head']}\n"
            f"camp_pointer_head={camp_head}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ),
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
        expected_authority={
            "r0_review_artifact": full_r_authority["r0_review_artifact"],
            "r0_review_root_sha256": full_r_authority[
                "r0_review_root_sha256"
            ],
            "r0_source_artifact": full_r_authority["r0_source_artifact"],
            "r0_source_root_sha256": full_r_authority[
                "r0_source_root_sha256"
            ],
            "ultra_full_config_preflight_release_artifact": full_r_authority[
                "preflight_release_artifact"
            ],
            "ultra_full_config_preflight_release_root_sha256": full_r_authority[
                "preflight_release_root_sha256"
            ],
            "semantic_authority_root_sha256": semantic_authority_root,
            "semantic_authority_identity_count": len(cases),
            "semantic_authority_chains_root_sha256": semantic_chain_root,
            "seven_root_bindings": full_r_authority["seven_root_bindings"],
            "seven_root_bindings_sha256": full_r_authority[
                "seven_root_bindings_sha256"
            ],
            "release_run_nonce": full_r_authority[
                "preflight_release_run_nonce"
            ],
            "release_nonce_consumption_marker": full_r_authority[
                "preflight_release_nonce_consumption_marker"
            ],
            "authorized_output_dir": full_r_authority[
                "preflight_authorized_output_dir"
            ],
            "critical_implementation_manifest": full_r_authority[
                "critical_implementation_manifest"
            ],
        },
        implementation_source_head=str(
            full_r_authority["implementation_source_head"]
        ),
        critical_implementation_manifest=full_r_authority[
            "critical_implementation_manifest"
        ],
        expected_dp_repo=args.dp_repo,
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


def _verify_a17_full_r_authority(
    *,
    release_artifact: Path,
    release_root_sha256: str,
    preflight_artifact: Path | None,
    preflight_review_artifact: Path | None,
    preflight_review_root_sha256: str | None,
    camp_head: str,
    mode: str,
    output_dir: Path,
    probe_template: Path,
    dp_repo: Path,
) -> dict[str, Any]:
    if mode not in {"preflight", "execute"}:
        raise ValueError("A1.7 full-corpus mode is invalid")
    verified = verify_a17_full_corpus_release(
        repo=ROOT,
        release_artifact=release_artifact,
        release_root_sha256=release_root_sha256,
        requested_output_dir=str(output_dir),
        current_pointer_head=camp_head,
        dp_repo=dp_repo,
        probe_template=probe_template,
        mode=mode,
        consume=True,
    )
    decision = verified["decision"]
    roots = decision["root_artifacts"]
    source = roots["source"]
    bounded_review = roots["bounded_execution_review"]
    marker = verified["nonce_marker"]
    if type(marker) is not dict:
        raise ValueError("A1.7 release nonce was not consumed")
    if mode == "preflight":
        if any(
            value is not None
            for value in (
                preflight_artifact,
                preflight_review_artifact,
                preflight_review_root_sha256,
            )
        ):
            raise ValueError("A1.7 preflight cannot consume prior preflight evidence")
        preflight_release_artifact = str(release_artifact.resolve())
        preflight_release_root = verified["release_root_sha256"]
        preflight_release_nonce = decision["run_nonce"]
        preflight_authorized_output = decision["authorized_output_dir"]
        preflight_release_nonce_consumption_marker = marker
    else:
        if (
            preflight_artifact is None
            or preflight_review_artifact is None
            or preflight_review_root_sha256 is None
            or Path(decision["preflight_artifact"]).resolve()
            != preflight_artifact.resolve()
            or Path(decision["preflight_review_artifact"]).resolve()
            != preflight_review_artifact.resolve()
            or decision["preflight_review_root_sha256"]
            != preflight_review_root_sha256
        ):
            raise ValueError("A1.7 execute CLI preflight bindings drifted")
        preflight_release_artifact = decision["preflight_release_artifact"]
        preflight_release_root = decision["preflight_release_root_sha256"]
        preflight_release_nonce = decision["preflight_release_run_nonce"]
        preflight_report = _load_json(preflight_artifact / "report.json")
        preflight_authorized_output = preflight_report["authorized_output_dir"]
        preflight_release_nonce_consumption_marker = preflight_report.get(
            "release_nonce_consumption_marker"
        )
        if (
            type(preflight_release_nonce_consumption_marker) is not dict
            or set(preflight_release_nonce_consumption_marker)
            != {"path", "sha256"}
            or type(preflight_release_nonce_consumption_marker.get("path"))
            is not str
            or not Path(
                preflight_release_nonce_consumption_marker["path"]
            ).is_absolute()
            or type(
                preflight_release_nonce_consumption_marker.get("sha256")
            )
            is not str
            or not _is_sha256(
                preflight_release_nonce_consumption_marker["sha256"]
            )
            or _file_sha256(
                Path(preflight_release_nonce_consumption_marker["path"])
            )
            != preflight_release_nonce_consumption_marker["sha256"]
        ):
            raise ValueError(
                "A1.7 sealed preflight nonce marker binding is invalid"
            )

    authority = {
        "r0_review_artifact": str(Path(bounded_review["path"]).resolve()),
        "r0_review_root_sha256": bounded_review["root_sha256"],
        "r0_source_artifact": str(Path(source["path"]).resolve()),
        "r0_source_root_sha256": source["root_sha256"],
        "preflight_release_artifact": preflight_release_artifact,
        "preflight_release_root_sha256": preflight_release_root,
        "preflight_review_artifact": None,
        "preflight_review_root_sha256": None,
        "execute_release_artifact": None,
        "execute_release_root_sha256": None,
        "implementation_source_head": decision["implementation_source_head"],
        "seven_root_bindings": {
            role: {
                "path": str(roots[role]["path"]),
                "root_sha256": str(roots[role]["root_sha256"]),
                "report_file": str(roots[role]["report_file"]),
            }
            for role in A17_UPSTREAM_ROLES
        },
        "seven_root_bindings_sha256": _canonical_sha256(roots),
        "release_run_nonce": decision["run_nonce"],
        "authorized_output_dir": decision["authorized_output_dir"],
        "preflight_release_run_nonce": preflight_release_nonce,
        "preflight_authorized_output_dir": preflight_authorized_output,
        "preflight_release_nonce_consumption_marker": (
            preflight_release_nonce_consumption_marker
        ),
        "critical_implementation_manifest": dict(
            decision["critical_implementation_manifest"]
        ),
        "release_nonce_consumption_marker": marker,
        "a17_full_corpus_authority": True,
        "route_source_producer_head": verified["upstream"][
            "bounded_source_head"
        ],
    }
    if mode == "execute":
        authority.update(
            {
                "preflight_review_artifact": str(
                    preflight_review_artifact.resolve()
                ),
                "preflight_review_root_sha256": preflight_review_root_sha256,
                "execute_release_artifact": str(release_artifact.resolve()),
                "execute_release_root_sha256": verified["release_root_sha256"],
            }
        )
    return authority


def _verify_full_r_authority(
    *,
    r0_review_artifact: Path | None,
    r0_review_root_sha256: str | None,
    r0_source_artifact: Path | None,
    r0_source_root_sha256: str | None,
    preflight_release_artifact: Path | None,
    preflight_release_root_sha256: str | None,
    preflight_artifact: Path | None,
    preflight_review_artifact: Path | None,
    preflight_review_root_sha256: str | None,
    execute_release_artifact: Path | None,
    execute_release_root_sha256: str | None,
    a17_release_artifact: Path | None,
    a17_release_root_sha256: str | None,
    camp_head: str,
    mode: str,
    output_dir: Path,
    probe_template: Path,
    dp_repo: Path,
) -> dict[str, Any]:
    if a17_release_artifact is not None or a17_release_root_sha256 is not None:
        if a17_release_artifact is None or a17_release_root_sha256 is None:
            raise ValueError("A1.7 full-corpus release path/root must be paired")
        if any(
            value is not None
            for value in (
                r0_review_artifact,
                r0_review_root_sha256,
                r0_source_artifact,
                r0_source_root_sha256,
                preflight_release_artifact,
                preflight_release_root_sha256,
                execute_release_artifact,
                execute_release_root_sha256,
            )
        ):
            raise ValueError("A1.7 authority cannot be mixed with historical releases")
        return _verify_a17_full_r_authority(
            release_artifact=a17_release_artifact,
            release_root_sha256=a17_release_root_sha256,
            preflight_artifact=preflight_artifact,
            preflight_review_artifact=preflight_review_artifact,
            preflight_review_root_sha256=preflight_review_root_sha256,
            camp_head=camp_head,
            mode=mode,
            output_dir=output_dir,
            probe_template=probe_template,
            dp_repo=dp_repo,
        )
    if (
        r0_review_artifact is None
        or r0_review_root_sha256 is None
        or r0_source_artifact is None
        or r0_source_root_sha256 is None
        or preflight_release_artifact is None
        or preflight_release_root_sha256 is None
        or mode not in {"preflight", "execute"}
    ):
        raise ValueError(
            "full R config preflight requires sealed R0 review and Ultra preflight release"
        )
    preflight_release_seal = verify_complete_seal(
        preflight_release_artifact,
        preflight_release_root_sha256,
        label="V25 Ultra full-config-preflight release",
    )
    preflight_release = _load_json(preflight_release_artifact / "decision.json")
    required_preflight_release_fields = {
        "schema_version",
        "status",
        "implementation_source_head",
        "pointer_head_at_release",
        "fixed_dp_head",
        "formal_artifact",
        "formal_root_sha256",
        "probe_template",
        "probe_template_sha256",
        "generation_scales",
        "static_weights",
        "dp_repo",
        "fixed_dp_checkpoint",
        "fixed_dp_args_json",
        "native_source_roots",
        "root_artifacts",
        "rejected_roots",
        "critical_implementation_manifest",
        "run_nonce",
        "authorized_output_dir",
        "full_config_preflight_authorized",
        "full_r_execute_authorized",
        "fresh_b2_opened",
        "outcome_fields_consumed",
    }
    if (
        (preflight_release_artifact / "run.exit").read_text(encoding="ascii")
        != "0\n"
        or set(preflight_release) != required_preflight_release_fields
        or preflight_release.get("schema_version")
        != PREFLIGHT_RELEASE_SCHEMA_VERSION
        or preflight_release.get("status") != "full_config_preflight_released"
        or preflight_release.get("full_config_preflight_authorized") is not True
        or preflight_release.get("full_r_execute_authorized") is not False
        or preflight_release.get("fixed_dp_head") != FIXED_DP_HEAD
        or Path(str(preflight_release.get("formal_artifact"))).resolve()
        != FORMAL_ARTIFACT.resolve()
        or preflight_release.get("formal_root_sha256") != FORMAL_ROOT_SHA256
        or Path(str(preflight_release.get("probe_template"))).resolve()
        != probe_template.resolve()
        or preflight_release.get("probe_template_sha256")
        != EXPECTED_TEMPLATE_SHA256
        or preflight_release.get("generation_scales")
        != {
            "path": str(CORRECTED_GENERATION_SCALES),
            "sha256": _file_sha256(CORRECTED_GENERATION_SCALES),
        }
        or Path(str(preflight_release.get("dp_repo"))).resolve()
        != dp_repo.resolve()
        or preflight_release.get("native_source_roots") != S01_NATIVE_SOURCE_ROOTS
        or preflight_release.get("rejected_roots")
        != [SUPERSEDED_PARTIAL_CORPUS_ROOT]
        or preflight_release.get("fresh_b2_opened") is not False
        or preflight_release.get("outcome_fields_consumed") != []
        or type(preflight_release.get("run_nonce")) is not str
        or not _is_sha256(preflight_release.get("run_nonce"))
        or type(preflight_release.get("authorized_output_dir")) is not str
        or not Path(preflight_release["authorized_output_dir"]).is_absolute()
        or preflight_release["authorized_output_dir"]
        != str(Path(preflight_release["authorized_output_dir"]).resolve())
    ):
        raise ValueError("full R config-preflight authority chain is invalid")
    release_template = _load_json(probe_template)
    fixed_template = release_template.get("fixed_dp")
    static_weights = release_template.get("selector", {}).get("weights")
    if (
        not isinstance(fixed_template, Mapping)
        or fixed_template.get("head") != FIXED_DP_HEAD
        or preflight_release.get("fixed_dp_checkpoint")
        != fixed_template.get("checkpoint")
        or preflight_release.get("fixed_dp_args_json")
        != fixed_template.get("args_json")
        or preflight_release.get("static_weights") != static_weights
        or _git_head(dp_repo) != FIXED_DP_HEAD
        or _tracked_dirty(dp_repo)
    ):
        raise ValueError("full R release fixed assets/live DP authority drifted")
    implementation_source_head = str(
        preflight_release["implementation_source_head"]
    )
    manifest = preflight_release["critical_implementation_manifest"]
    if not isinstance(manifest, Mapping):
        raise ValueError("critical implementation manifest is invalid")
    verify_dual_head_contract(
        repo=ROOT,
        implementation_source_head=implementation_source_head,
        current_pointer_head=str(preflight_release["pointer_head_at_release"]),
        implementation_manifest=manifest,
    )
    verify_dual_head_contract(
        repo=ROOT,
        implementation_source_head=implementation_source_head,
        current_pointer_head=camp_head,
        implementation_manifest=manifest,
    )
    root_bindings = preflight_release["root_artifacts"]
    if not isinstance(root_bindings, Mapping):
        raise ValueError("seven-root release bindings are invalid")
    verified_roots = verify_seven_root_chain(
        bindings=root_bindings,
        implementation_source_head=implementation_source_head,
        fixed_dp_head=FIXED_DP_HEAD,
        rejected_root_sha256=SUPERSEDED_PARTIAL_CORPUS_ROOT,
    )
    source_binding = root_bindings["r01_source"]
    review_binding = root_bindings["r01_bounded_review"]
    if (
        Path(str(source_binding["path"])).resolve() != r0_source_artifact.resolve()
        or source_binding["root_sha256"] != r0_source_root_sha256
        or Path(str(review_binding["path"])).resolve() != r0_review_artifact.resolve()
        or review_binding["root_sha256"] != r0_review_root_sha256
    ):
        raise ValueError("CLI R0 roots do not match the seven-root release")
    source_seal = {
        "root_sha256": verified_roots["r01_source"]["root_sha256"]
    }
    review_seal = {
        "root_sha256": verified_roots["r01_bounded_review"]["root_sha256"]
    }
    authority: dict[str, Any] = {
        "r0_review_artifact": str(r0_review_artifact),
        "r0_review_root_sha256": review_seal["root_sha256"],
        "r0_source_artifact": str(r0_source_artifact),
        "r0_source_root_sha256": source_seal["root_sha256"],
        "preflight_release_artifact": str(preflight_release_artifact),
        "preflight_release_root_sha256": preflight_release_seal["root_sha256"],
        "preflight_review_artifact": None,
        "preflight_review_root_sha256": None,
        "execute_release_artifact": None,
        "execute_release_root_sha256": None,
        "implementation_source_head": implementation_source_head,
        "seven_root_bindings": {
            role: {
                "path": str(root_bindings[role]["path"]),
                "root_sha256": str(root_bindings[role]["root_sha256"]),
                "report_file": str(root_bindings[role]["report_file"]),
            }
            for role in ROOT_ROLES
        },
        "seven_root_bindings_sha256": _canonical_sha256(root_bindings),
        "release_run_nonce": preflight_release["run_nonce"],
        "authorized_output_dir": preflight_release["authorized_output_dir"],
        "preflight_release_run_nonce": preflight_release["run_nonce"],
        "preflight_authorized_output_dir": preflight_release[
            "authorized_output_dir"
        ],
        "critical_implementation_manifest": dict(manifest),
    }
    if mode == "preflight":
        if any(
            value is not None
            for value in (
                preflight_artifact,
                preflight_review_artifact,
                preflight_review_root_sha256,
                execute_release_artifact,
                execute_release_root_sha256,
            )
        ):
            raise ValueError("full-config preflight cannot consume execute authority")
        marker = consume_one_shot_nonce(
            ledger_dir=RELEASE_NONCE_LEDGER,
            gate="preflight",
            nonce=preflight_release["run_nonce"],
            authorized_output_dir=preflight_release["authorized_output_dir"],
            requested_output_dir=output_dir,
        )
        authority["release_nonce_consumption_marker"] = {
            "path": str(marker),
            "sha256": _file_sha256(marker),
        }
        return authority
    if (
        preflight_artifact is None
        or preflight_review_artifact is None
        or preflight_review_root_sha256 is None
        or execute_release_artifact is None
        or execute_release_root_sha256 is None
    ):
        raise ValueError(
            "full R execute requires sealed config preflight review and Ultra execute release"
        )
    preflight_seal = verify_complete_seal(
        preflight_artifact, None, label="V25 full-config preflight"
    )
    preflight_review_seal = verify_complete_seal(
        preflight_review_artifact,
        preflight_review_root_sha256,
        label="V25 full-config preflight review",
    )
    execute_release_seal = verify_complete_seal(
        execute_release_artifact,
        execute_release_root_sha256,
        label="V25 Ultra full-R execute release",
    )
    preflight_review = _load_json(preflight_review_artifact / "report.json")
    execute_release = _load_json(execute_release_artifact / "decision.json")
    required_execute_fields = {
        "schema_version",
        "status",
        "implementation_source_head",
        "pointer_head_at_release",
        "fixed_dp_head",
        "root_artifacts",
        "rejected_roots",
        "critical_implementation_manifest",
        "run_nonce",
        "authorized_output_dir",
        "preflight_release_root_sha256",
        "full_config_preflight_root_sha256",
        "full_config_preflight_review_root_sha256",
        "full_r_execute_authorized",
        "fresh_b2_opened",
        "outcome_fields_consumed",
    }
    if (
        (preflight_artifact / "run.exit").read_text(encoding="ascii") != "0\n"
        or (preflight_review_artifact / "run.exit").read_text(encoding="ascii")
        != "0\n"
        or (execute_release_artifact / "run.exit").read_text(encoding="ascii")
        != "0\n"
        or preflight_review.get("status")
        != "passed_independent_1500_config_preflight_review_execute_closed"
        or preflight_review.get("reviewed_root_sha256")
        != preflight_seal["root_sha256"]
        or preflight_review.get("identity_count") != 1500
        or set(execute_release) != required_execute_fields
        or execute_release.get("schema_version")
        != EXECUTE_RELEASE_SCHEMA_VERSION
        or execute_release.get("status") != "full_R_execute_released"
        or execute_release.get("implementation_source_head")
        != implementation_source_head
        or execute_release.get("root_artifacts") != root_bindings
        or execute_release.get("rejected_roots")
        != [SUPERSEDED_PARTIAL_CORPUS_ROOT]
        or execute_release.get("critical_implementation_manifest") != manifest
        or execute_release.get("fixed_dp_head") != FIXED_DP_HEAD
        or execute_release.get("preflight_release_root_sha256")
        != preflight_release_seal["root_sha256"]
        or execute_release.get("full_config_preflight_root_sha256")
        != preflight_seal["root_sha256"]
        or execute_release.get("full_config_preflight_review_root_sha256")
        != preflight_review_seal["root_sha256"]
        or execute_release.get("full_r_execute_authorized") is not True
        or execute_release.get("fresh_b2_opened") is not False
        or execute_release.get("outcome_fields_consumed") != []
        or type(execute_release.get("run_nonce")) is not str
        or not _is_sha256(execute_release.get("run_nonce"))
        or type(execute_release.get("authorized_output_dir")) is not str
        or not Path(execute_release["authorized_output_dir"]).is_absolute()
        or execute_release["authorized_output_dir"]
        != str(Path(execute_release["authorized_output_dir"]).resolve())
    ):
        raise ValueError("full R execute authority chain is invalid")
    verify_dual_head_contract(
        repo=ROOT,
        implementation_source_head=implementation_source_head,
        current_pointer_head=str(execute_release["pointer_head_at_release"]),
        implementation_manifest=manifest,
    )
    marker = consume_one_shot_nonce(
        ledger_dir=RELEASE_NONCE_LEDGER,
        gate="execute",
        nonce=execute_release["run_nonce"],
        authorized_output_dir=execute_release["authorized_output_dir"],
        requested_output_dir=output_dir,
    )
    authority.update(
        {
            "preflight_review_artifact": str(preflight_review_artifact),
            "preflight_review_root_sha256": preflight_review_seal["root_sha256"],
            "execute_release_artifact": str(execute_release_artifact),
            "execute_release_root_sha256": execute_release_seal["root_sha256"],
            "release_run_nonce": execute_release["run_nonce"],
            "authorized_output_dir": execute_release["authorized_output_dir"],
            "release_nonce_consumption_marker": {
                "path": str(marker),
                "sha256": _file_sha256(marker),
            },
        }
    )
    return authority


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


def _route_polyline_from_builder(
    builder: Any, route_lanelet_ids: list[int]
) -> np.ndarray:
    pieces: list[np.ndarray] = []
    for lanelet_id in route_lanelet_ids:
        cached = builder._cache.get(lanelet_id)
        if cached is None:
            raise ValueError("formal route lanelet is absent from map cache")
        values = np.asarray(cached.raw_centerline, dtype=np.float64)
        if (
            values.ndim != 2
            or values.shape[1] != 2
            or len(values) < 2
            or not np.isfinite(values).all()
        ):
            raise ValueError("formal route lanelet geometry is invalid")
        pieces.append(values if not pieces else values[1:])
    if not pieces:
        raise ValueError("formal route has no lanelets")
    polyline = np.concatenate(pieces, axis=0)
    if len(polyline) < 2:
        raise ValueError("formal route geometry has fewer than two points")
    return polyline


def _attach_semantic_clone_authority(
    cases: list[Mapping[str, Any]],
    *,
    dp_repo: Path,
    r0_source_artifact: Path,
    expected_camp_source_head: str,
    r0_source_root_sha256: str,
) -> list[dict[str, Any]]:
    """Bind every R identity to sealed route-level source authority, not family."""
    source_payload = _load_json(
        r0_source_artifact / "route_signal_source_receipts.json"
    )
    source_rows = source_payload.get("cases")
    if (
        set(source_payload)
        != {
            "schema_version",
            "formal_artifact",
            "formal_root_sha256",
            "camp_source_head",
            "fixed_dp_head",
            "cases",
            "source_failures",
        }
        or source_payload.get("schema_version")
        != ROUTE_SIGNAL_SOURCE_RECEIPTS_SCHEMA_VERSION
        or Path(str(source_payload.get("formal_artifact"))).resolve()
        != FORMAL_ARTIFACT.resolve()
        or source_payload.get("formal_root_sha256") != FORMAL_ROOT_SHA256
        or source_payload.get("fixed_dp_head") != FIXED_DP_HEAD
        or source_payload.get("camp_source_head") != expected_camp_source_head
        or not isinstance(source_rows, list)
        or len(source_rows) != EXPECTED_EXECUTABLE_IDENTITIES + EXPECTED_RETAINED_INELIGIBLE
        or source_payload.get("source_failures") != []
    ):
        raise ValueError("route-level source authority denominator drifted")
    source_row_fields = {
        "scenario_id",
        "formal_case_sha256",
        "runner_eligible",
        "retention_role",
        "family",
        "tier",
        "seed",
        "source_map_sha256",
        "route_identity_sha256",
        "actual_mapped_signal",
        "id_free_tensor_layout",
        "source_class",
        "phase_authority_mode",
        "source_chain",
        "runtime_receipt",
        "tensor_evidence",
    }
    if any(
        not isinstance(row, Mapping) or set(row) != source_row_fields
        for row in source_rows
    ):
        raise ValueError("route-level source authority row schema drifted")
    rows = {str(row.get("scenario_id")): row for row in source_rows}
    if len(rows) != len(source_rows):
        raise ValueError("route-level source authority identities are not unique")

    for path in (dp_repo, dp_repo / "diffusion_planner"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder

    builders: dict[str, Any] = {}
    enriched: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_case in cases:
        case = json.loads(json.dumps(raw_case))
        map_path = str(case["source_map_path"])
        if map_path not in builders:
            source_path = Path(map_path)
            require_source_preserving_lanelet2_regulatory_adapter(source_path)
            sys.modules.pop(
                "autoware_lanelet2_extension_python.projection", None
            )
            sys.modules.pop("autoware_lanelet2_extension_python", None)
            install_lanelet2_projection_fallback(source_path)
            builders[map_path] = LaneletSceneBuilder(map_path)
        route_ids = [int(value) for value in case["route_spec"]["lanelet_ids"]]
        route_polyline = _route_polyline_from_builder(
            builders[map_path], route_ids
        )
        scenario_id = str(case["scenario_id"])
        row = rows.get(scenario_id)
        if not isinstance(row, Mapping) or row.get("runner_eligible") is not True:
            raise ValueError("formal executable identity lacks route-level source authority")
        if (
            row.get("formal_case_sha256") != canonical_json_sha256(raw_case)
            or row.get("route_identity_sha256") != case["route_identity_sha256"]
            or row.get("source_map_sha256") != case["source_map_sha256"]
        ):
            raise ValueError("route-level source authority does not match formal case")
        source_class = row.get("source_class")
        chain = row.get("source_chain")
        if source_class == "mapped_signal":
            chain = validate_mapped_signal_chain(chain)
            if chain["route_lanelet_ids"] != route_ids:
                raise ValueError("mapped-signal route authority lanelets drifted")
            semantic = build_semantic_clone_payload(
                case,
                route_polyline_world=route_polyline,
                stop_line_world=np.asarray(
                    chain["stop_line_geometry_m"], dtype=np.float64
                ),
            )
            if canonical_json_sha256(semantic) != chain["semantic_clone_sha256"]:
                raise ValueError("mapped semantic clone hash does not match source")
            case["mapped_signal_authority"] = chain
            case["phase_authority_mode"] = chain["phase_authority_mode"]
        elif source_class == "no_signal":
            chain = validate_no_signal_chain(chain)
            if chain["route_lanelet_ids"] != route_ids:
                raise ValueError("no-signal route authority lanelets drifted")
            semantic = build_semantic_clone_payload(
                case,
                route_polyline_world=route_polyline,
                stop_line_world=None,
            )
            if canonical_json_sha256(semantic) != chain["semantic_clone_sha256"]:
                raise ValueError("no-signal semantic clone hash does not match source")
            case["no_signal_authority"] = chain
            case["phase_authority_mode"] = None
        else:
            raise ValueError("route-level source class is invalid")
        case["signal_source_class"] = source_class
        case["route_signal_source_artifact_root_sha256"] = r0_source_root_sha256
        case["route_signal_source_row_sha256"] = _canonical_sha256(row)
        case["canonical_semantic_clone_sha256"] = canonical_json_sha256(
            semantic
        )
        enriched.append(case)
        seen.add(scenario_id)
    if seen != {str(case["scenario_id"]) for case in cases}:
        raise ValueError("route-level source authority coverage drifted")
    return enriched


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
    # main() already holds TRAIN_LOCK from before output creation through seal.
    # A second flock probe on a second file descriptor would reject the owning
    # process itself on Linux, so the bounded preflight must not re-lock here.
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
    plan, _formal_root = _load_formal_plan()
    retained_ineligible = _retained_ineligible_authority_receipts(plan)
    return {
        **dict(common),
        "static_weights": dict(shared["selector"]["weights"]),
        "config_receipts_root_sha256": config_root,
        "mode": "preflight",
        "status": "passed",
        "validated_identity_count": len(receipts),
        "source_ineligible_retained_identity_count": EXPECTED_RETAINED_INELIGIBLE,
        "retained_ineligible_receipts": retained_ineligible,
        "retained_ineligible_receipts_root_sha256": _canonical_sha256(
            retained_ineligible
        ),
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


def _retained_ineligible_authority_receipts(
    plan: Mapping[str, Any],
) -> list[dict[str, Any]]:
    receipts = []
    for case in plan["train"]:
        if case.get("runner_eligible") is not False:
            continue
        receipts.append(
            {
                "scenario_id": str(case["scenario_id"]),
                "family": str(case["family"]),
                "tier": str(case["tier"]),
                "route_identity_sha256": str(case["route_identity_sha256"]),
                "source_map_sha256": str(case["source_map_sha256"]),
                "source_requirements": list(case["source_requirements"]),
                "source_availability": dict(case["source_availability"]),
                "retention_role": str(case["retention_role"]),
            }
        )
    if len(receipts) != EXPECTED_RETAINED_INELIGIBLE:
        raise ValueError("retained source-ineligible denominator drifted")
    return receipts


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
        "canonical_semantic_clone_sha256": str(
            controlled["canonical_semantic_clone_sha256"]
        ),
        "signal_source_chain_sha256": str(
            (
                controlled.get("mapped_signal_authority")
                or controlled.get("no_signal_authority")
            )["source_chain_sha256"]
        ),
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


def _preflight_nonce_marker_matches(
    payload: Any, *, nonce: Any, authorized_output_dir: Any
) -> bool:
    if (
        type(nonce) is not str
        or not _is_sha256(nonce)
        or type(authorized_output_dir) is not str
        or not authorized_output_dir
    ):
        return False
    authorized = Path(authorized_output_dir)
    if not authorized.is_absolute() or authorized_output_dir != str(authorized.resolve()):
        return False
    if not isinstance(payload, Mapping) or set(payload) != {"path", "sha256"}:
        return False
    path = Path(str(payload["path"]))
    legacy = RELEASE_NONCE_LEDGER / f"v25_preflight_{nonce}.consumed.json"
    a17 = A17_FULL_CORPUS_NONCE_LEDGER / (
        f"v25_{A17_FULL_CONFIG_PREFLIGHT_GATE}_{nonce}.consumed.json"
    )
    expected = a17 if path.resolve() == a17.resolve() else legacy
    if (
        path.resolve() != expected.resolve()
        or not path.is_file()
        or _file_sha256(path) != payload["sha256"]
    ):
        return False
    marker = _load_json(path)
    return marker == {
        "gate": (
            A17_FULL_CONFIG_PREFLIGHT_GATE
            if expected == a17
            else "preflight"
        ),
        "nonce": nonce,
        "authorized_output_dir": authorized_output_dir,
    }


def _verify_preflight(
    path: Path,
    camp_head: str,
    *,
    expected_config_root_sha256: str,
    expected_authority: Mapping[str, Any],
    implementation_source_head: str,
    critical_implementation_manifest: Mapping[str, Any],
    expected_dp_repo: Path,
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
        "canonical_json_byte_spec",
        "status",
        "mode",
        "camp_head",
        "implementation_source_head",
        "released_camp_source_head",
        "current_repo_head_at_run",
        "fixed_dp_head",
        "dp_repo",
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
        "train_lock",
        "minimum_free_bytes",
        "validated_identity_count",
        "source_ineligible_retained_identity_count",
        "retained_ineligible_receipts",
        "retained_ineligible_receipts_root_sha256",
        "formal_train_manifest_identity_count",
        "unique_route_count",
        "family_counts",
        "tier_counts",
        "model_loaded",
        "candidate_generation_started",
        "simulator_started",
        "training_executed",
        "calibration_executed",
        "claim_authorized",
        "fresh_b_opened",
        "outcome_fields_consumed",
        "config_receipts",
        "rejected_roots",
        "r0_review_artifact",
        "r0_review_root_sha256",
        "r0_source_artifact",
        "r0_source_root_sha256",
        "ultra_full_config_preflight_release_artifact",
        "ultra_full_config_preflight_release_root_sha256",
        "semantic_authority_root_sha256",
        "semantic_authority_identity_count",
        "semantic_authority_chains_root_sha256",
        "seven_root_bindings",
        "seven_root_bindings_sha256",
        "release_run_nonce",
        "release_nonce_consumption_marker",
        "authorized_output_dir",
        "critical_implementation_manifest",
        "terminal_lock_scope",
        "free_bytes_at_start",
    }
    integer_fields = (
        "seed",
        "corpus_steps",
        "snapshot_capacity",
        "minimum_free_bytes",
        "free_bytes_at_start",
        "validated_identity_count",
        "source_ineligible_retained_identity_count",
        "formal_train_manifest_identity_count",
        "unique_route_count",
        "semantic_authority_identity_count",
    )
    boolean_fields = (
        "model_loaded",
        "candidate_generation_started",
        "simulator_started",
        "training_executed",
        "calibration_executed",
        "claim_authorized",
        "fresh_b_opened",
    )
    if (
        set(report) != required_keys
        or any(type(report.get(field)) is not int for field in integer_fields)
        or any(type(report.get(field)) is not bool for field in boolean_fields)
        or type(report.get("release_run_nonce")) is not str
        or not _is_sha256(report.get("release_run_nonce"))
        or type(report.get("authorized_output_dir")) is not str
        or not Path(report["authorized_output_dir"]).is_absolute()
        or report["authorized_output_dir"]
        != str(Path(report["authorized_output_dir"]).resolve())
        or report.get("status") != "passed"
        or report.get("mode") != "preflight"
        or report.get("schema_version") != SCHEMA_VERSION
        or report.get("canonical_json_byte_spec")
        != CANONICAL_JSON_BYTE_SPEC_VERSION
        or report.get("implementation_source_head")
        != implementation_source_head
        or report.get("released_camp_source_head")
        != implementation_source_head
        or report.get("camp_head") != report.get("current_repo_head_at_run")
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or Path(str(report.get("dp_repo"))).resolve() != expected_dp_repo.resolve()
        or report.get("formal_artifact") != str(FORMAL_ARTIFACT)
        or report.get("formal_root_sha256") != FORMAL_ROOT_SHA256
        or not Path(str(report.get("probe_template"))).is_file()
        or _file_sha256(Path(str(report.get("probe_template"))))
        != EXPECTED_TEMPLATE_SHA256
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
        or report.get("source_ineligible_retained_identity_count")
        != EXPECTED_RETAINED_INELIGIBLE
        or report.get("formal_train_manifest_identity_count")
        != EXPECTED_EXECUTABLE_IDENTITIES + EXPECTED_RETAINED_INELIGIBLE
        or report.get("retained_ineligible_receipts_root_sha256")
        != _canonical_sha256(report.get("retained_ineligible_receipts"))
        or report.get("model_loaded") is not False
        or report.get("candidate_generation_started") is not False
        or report.get("simulator_started") is not False
        or report.get("training_executed") is not False
        or report.get("calibration_executed") is not False
        or report.get("claim_authorized") is not False
        or report.get("fresh_b_opened") is not False
        or report.get("outcome_fields_consumed") != []
        or report.get("train_lock") != str(TRAIN_LOCK)
        or report.get("minimum_free_bytes") != MINIMUM_FREE_BYTES
        or type(report.get("free_bytes_at_start")) is not int
        or report.get("free_bytes_at_start") < MINIMUM_FREE_BYTES
        or report.get("terminal_lock_scope")
        != "preflight_or_execution_from_before_output_creation_through_progress_report_run_exit_and_seal"
        or not _preflight_nonce_marker_matches(
            report.get("release_nonce_consumption_marker"),
            nonce=report.get("release_run_nonce"),
            authorized_output_dir=report.get("authorized_output_dir"),
        )
        or report.get("rejected_roots") != [SUPERSEDED_PARTIAL_CORPUS_ROOT]
        or any(report.get(key) != value for key, value in expected_authority.items())
        or not all(
            isinstance(report.get(key), str) and report.get(key)
            for key in (
                "r0_review_artifact",
                "r0_source_artifact",
                "ultra_full_config_preflight_release_artifact",
            )
        )
        or not all(
            _is_sha256(report.get(key))
            for key in (
                "r0_review_root_sha256",
                "r0_source_root_sha256",
                "ultra_full_config_preflight_release_root_sha256",
                "semantic_authority_root_sha256",
            )
        )
        or report.get("corpus_steps") != CORPUS_STEPS
        or report.get("snapshot_capacity")
        != EXPECTED_EXECUTABLE_IDENTITIES * CORPUS_STEPS
        or report.get("training_executed") is not False
        or report.get("calibration_executed") is not False
        or report.get("fresh_b_opened") is not False
        or source_receipt != report
        or run_exit != "0\n"
        or not command
        or heads
        != [
            f"camp_source_head={implementation_source_head}",
            f"camp_pointer_head={report.get('camp_head')}",
            f"fixed_dp_head={FIXED_DP_HEAD}",
        ]
    ):
        raise ValueError("controlled train preflight authority is invalid")
    verify_dual_head_contract(
        repo=ROOT,
        implementation_source_head=implementation_source_head,
        current_pointer_head=str(report["camp_head"]),
        implementation_manifest=critical_implementation_manifest,
    )
    verify_dual_head_contract(
        repo=ROOT,
        implementation_source_head=implementation_source_head,
        current_pointer_head=camp_head,
        implementation_manifest=critical_implementation_manifest,
    )
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
                    adapter = V25ControlledSceneAdapter(
                        case,
                        mapped_signal_authority=case.get("mapped_signal_authority"),
                        no_signal_authority=case.get("no_signal_authority"),
                    )
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
                    except FixedDpCandidateGenerationCapabilityFailure as exc:
                        status = "failed"
                        failure_type = type(exc).__name__
                        failure_reason = str(exc)
                        capability_failure = _write_fixed_dp_capability_failure(
                            output_dir=output_dir,
                            case=case,
                            failure=exc,
                        )
                        snapshots.clear()
                        contexts.clear()
                        receipt_tick_count = 0
                        native_dir = (
                            output_dir / "native_runs" / str(case["scenario_id"])
                        )
                        if native_dir.exists():
                            shutil.rmtree(native_dir)
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
                                controlled_scene_receipt=adapter.receipts[
                                    tick_index
                                ],
                            ))
                    paired_count = len(payloads)
                    for tick_index, payload in enumerate(payloads):
                        _write_content_addressed_snapshot(
                            output_dir=output_dir,
                            index_file=index_file,
                            scenario_id=str(case["scenario_id"]),
                            tick_index=tick_index,
                            payload=payload,
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
        expected_support_authority={
            str(case["scenario_id"]): {
                "family": str(case["family"]),
                "tier": str(case["tier"]),
                "route_identity_sha256": str(case["route_identity_sha256"]),
                "source_class": str(case["signal_source_class"]),
                "phase_authority_mode": case["phase_authority_mode"],
                "source_map_sha256": str(case["source_map_sha256"]),
                "corridor_group_sha256": str(case["corridor_group_sha256"]),
            }
            for case in cases
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
        "retained_scenario_capability_failure_count": terminal[
            "retained_scenario_capability_failure_count"
        ],
        "retained_fixed_dp_capability_failure_count": terminal[
            "retained_fixed_dp_capability_failure_count"
        ],
        "red_scientific_coverage": terminal["red_scientific_coverage"],
        "fixed_dp_support_coverage": terminal["fixed_dp_support_coverage"],
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


def _strict_json_numeric_array(
    value: Any,
    shape: tuple[int, ...],
    *,
    label: str,
    dtype: np.dtype[Any] = np.dtype(np.float64),
) -> np.ndarray:
    """Reject bool/string/ragged/nonfinite numeric snapshot encodings."""
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a JSON list")

    def flatten(node: Any, depth: int) -> list[float]:
        if depth == len(shape):
            if type(node) not in (int, float) or not np.isfinite(float(node)):
                raise ValueError(f"{label} elements must be finite native numbers")
            return [float(node)]
        if not isinstance(node, list) or len(node) != shape[depth]:
            raise ValueError(f"{label} shape drifted")
        flattened: list[float] = []
        for child in node:
            flattened.extend(flatten(child, depth + 1))
        return flattened

    return np.asarray(flatten(value, 0), dtype=dtype).reshape(shape)


def _signal_tensors_from_evidence(
    evidence: Mapping[str, Any], *, tick_index: int
) -> tuple[np.ndarray, list[int], np.ndarray, list[int]]:
    required = {
        "schema_version",
        "tick_index",
        "decision_timestamp_s",
        "source_timestamp_s",
        "route_signal_rows",
        "map_signal_rows",
        "current_phase",
        "route_signal_tensor_sha256",
        "map_signal_tensor_sha256",
        "future_schedule_consumed",
        "phase_remaining_available",
    }
    if (
        not isinstance(evidence, Mapping)
        or set(evidence) != required
        or evidence.get("schema_version")
        != "camp_dp_v25_production_signal_tensor_evidence_v2"
        or type(evidence.get("tick_index")) is not int
        or evidence.get("tick_index") != tick_index
        or type(evidence.get("decision_timestamp_s")) not in (int, float)
        or type(evidence.get("source_timestamp_s")) not in (int, float)
        or not np.isfinite(float(evidence.get("decision_timestamp_s")))
        or not np.isfinite(float(evidence.get("source_timestamp_s")))
        or not np.isclose(
            float(evidence.get("decision_timestamp_s")),
            0.1 * tick_index,
            rtol=0.0,
            atol=1e-12,
        )
        or evidence.get("source_timestamp_s")
        != evidence.get("decision_timestamp_s")
        or evidence.get("current_phase") not in {"green", "yellow", "red"}
        or not _is_sha256(evidence.get("route_signal_tensor_sha256"))
        or not _is_sha256(evidence.get("map_signal_tensor_sha256"))
        or evidence.get("future_schedule_consumed") is not False
        or evidence.get("phase_remaining_available") is not False
    ):
        raise ValueError("production signal tensor evidence schema drifted")

    def materialize(rows: Any, expected_sha: Any) -> tuple[np.ndarray, list[int]]:
        if not isinstance(rows, list) or canonical_json_sha256(rows) != expected_sha:
            raise ValueError("production signal-row evidence root drifted")
        ids: list[int] = []
        arrays: list[np.ndarray] = []
        for row in rows:
            if not isinstance(row, Mapping) or set(row) != {
                "lanelet_id",
                "signal_channels_8_12",
            }:
                raise ValueError("production signal-row schema drifted")
            if type(row["lanelet_id"]) is not int:
                raise ValueError("production signal-row lanelet ID type drifted")
            raw_values = row["signal_channels_8_12"]
            if not isinstance(raw_values, list):
                raise ValueError("production signal-row values are invalid")
            values = _strict_json_numeric_array(
                raw_values,
                (len(raw_values), 5),
                label="production signal-row values",
            )
            ids.append(row["lanelet_id"])
            arrays.append(values)
        if len(ids) != len(set(ids)):
            raise ValueError("production signal-row lanelet IDs are duplicated")
        points = arrays[0].shape[0] if arrays else 20
        if any(array.shape != (points, 5) for array in arrays):
            raise ValueError("production signal-row shapes differ")
        tensor = np.zeros((len(arrays), points, 13), dtype=np.float64)
        for index, values in enumerate(arrays):
            tensor[index, :, 8:13] = values
        return tensor, ids

    route, route_ids = materialize(
        evidence["route_signal_rows"], evidence["route_signal_tensor_sha256"]
    )
    mapped, map_ids = materialize(
        evidence["map_signal_rows"], evidence["map_signal_tensor_sha256"]
    )
    return route, route_ids, mapped, map_ids


def combine_snapshot_context(
    *,
    snapshot: Mapping[str, Any],
    context: Mapping[str, Any],
    case: Mapping[str, Any],
    tick_index: int,
    controlled_scene_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if snapshot.get("schema_version") != "v22_native_decision_snapshot_v1":
        raise ValueError("native snapshot schema mismatch")
    features = snapshot.get("feature_payload")
    sidecar = snapshot.get("sidecar")
    raw = context.get("raw_context")
    source_complete = context.get("source_complete")
    source_receipt = context.get("source_receipt")
    causal_evidence = features.get("causal_evidence") if isinstance(features, Mapping) else None
    if (
        context.get("schema_version") != CONTEXT_SCHEMA_VERSION
        or not all(
            isinstance(value, Mapping)
            for value in (features, sidecar, raw, source_complete, source_receipt)
        )
    ):
        raise ValueError("controlled snapshot/context payload is malformed")
    atoms = _strict_json_numeric_array(
        features.get("atom_matrix"), (8, 14), label="atom_matrix"
    )
    candidate_tensor = validate_fixed_k8_candidate_tensor(
        _strict_json_numeric_array(
            features.get("candidate_tensor"),
            (8, 80, 4),
            label="candidate_tensor",
            dtype=np.dtype(np.float32),
        )
    )
    default_output = _strict_json_numeric_array(
        features.get("default_output"),
        (80, 4),
        label="default_output",
        dtype=np.dtype(np.float32),
    )
    expected_causal_fields = {
        "schema_version",
        "ego_current_state",
        "ego_shape",
        "neighbor_agents_past",
        "neighbor_valid_mask",
        "candidate_neighbor_predictions",
        "static_objects",
        "route_lanes",
        "route_lanes_speed_limit",
        "route_lanes_has_speed_limit",
        "signal_mask",
        "fixed_dp_planned_red_light_cost",
    }
    if (
        not isinstance(causal_evidence, Mapping)
        or set(causal_evidence) != expected_causal_fields
        or causal_evidence.get("schema_version")
        != "camp_dp_v25_bounded_causal_evidence_v1"
    ):
        raise ValueError("controlled snapshot causal-evidence schema drifted")
    causal_arrays = {
        "ego_current_state": _strict_json_numeric_array(
            causal_evidence.get("ego_current_state"), (10,), label="ego current state",
            dtype=np.dtype(np.float32),
        ),
        "ego_shape": _strict_json_numeric_array(
            causal_evidence.get("ego_shape"), (3,), label="ego shape",
            dtype=np.dtype(np.float32),
        ),
        "neighbor_agents_past": _strict_json_numeric_array(
            causal_evidence.get("neighbor_agents_past"), (32, 31, 11),
            label="neighbor history", dtype=np.dtype(np.float32),
        ),
        "candidate_neighbor_predictions": _strict_json_numeric_array(
            causal_evidence.get("candidate_neighbor_predictions"), (8, 32, 80, 4),
            label="candidate neighbor predictions", dtype=np.dtype(np.float32),
        ),
        "static_objects": _strict_json_numeric_array(
            causal_evidence.get("static_objects"), (5, 10), label="static objects",
            dtype=np.dtype(np.float32),
        ),
        "route_lanes": _strict_json_numeric_array(
            causal_evidence.get("route_lanes"), (25, 20, 33), label="route lanes",
            dtype=np.dtype(np.float32),
        ),
        "route_lanes_speed_limit": _strict_json_numeric_array(
            causal_evidence.get("route_lanes_speed_limit"), (25, 1),
            label="route speed limits", dtype=np.dtype(np.float32),
        ),
        "fixed_dp_planned_red_light_cost": _strict_json_numeric_array(
            causal_evidence.get("fixed_dp_planned_red_light_cost"), (8,),
            label="fixed DP planned red cost",
        ),
    }
    for name, shape in (
        ("neighbor_valid_mask", (32,)),
        ("route_lanes_has_speed_limit", (25, 1)),
        ("signal_mask", (8,)),
    ):
        raw_mask = causal_evidence.get(name)
        array = np.asarray(raw_mask)
        if (
            not isinstance(raw_mask, list)
            or array.shape != shape
            or array.dtype != np.bool_
        ):
            raise ValueError(f"controlled causal {name} must be strict bool{shape}")
        causal_arrays[name] = array
    causal_sha = _canonical_sha256(causal_evidence)
    if (
        sidecar.get("causal_evidence_sha256") != causal_sha
        or sidecar.get("route_lanes_sha256")
        != hashlib.sha256(np.ascontiguousarray(causal_arrays["route_lanes"]).tobytes()).hexdigest()
        or sidecar.get("route_lanes_speed_limit_sha256")
        != hashlib.sha256(
            np.ascontiguousarray(causal_arrays["route_lanes_speed_limit"]).tobytes()
        ).hexdigest()
        or sidecar.get("route_lanes_has_speed_limit_sha256")
        != hashlib.sha256(
            np.ascontiguousarray(causal_arrays["route_lanes_has_speed_limit"]).tobytes()
        ).hexdigest()
    ):
        raise ValueError("controlled causal route evidence SHA binding drifted")
    valid = features.get("source_valid_mask")
    atom_source_valid = np.asarray(features.get("atom_source_valid_mask"))
    atom_applicable = np.asarray(features.get("atom_applicable_mask"))
    rows = features.get("candidate_row_sha256")
    if (
        atoms.shape != (8, 14)
        or candidate_tensor.shape != (8, 80, 4)
        or default_output.shape != (80, 4)
        or not np.isfinite(atoms).all()
        or not np.isfinite(candidate_tensor).all()
        or not np.isfinite(default_output).all()
        or np.any(atoms < 0.0)
        or not isinstance(valid, list)
        or len(valid) != 8
        or any(not isinstance(value, bool) for value in valid)
        or not isinstance(rows, list)
        or len(rows) != 8
        or any(not _is_sha256(value) for value in rows)
        or atom_source_valid.dtype != np.bool_
        or atom_applicable.dtype != np.bool_
        or atom_source_valid.shape != (8, 14)
        or atom_applicable.shape != (8, 14)
        or np.any(atom_applicable & ~atom_source_valid)
        or not np.array_equal(
            np.asarray(valid, dtype=np.bool_), atom_source_valid.all(axis=1)
        )
    ):
        raise ValueError("controlled snapshot atoms/masks are invalid")
    candidate_rows = [
        hashlib.sha256(np.ascontiguousarray(candidate_tensor[index]).tobytes()).hexdigest()
        for index in range(8)
    ]
    default_sha = hashlib.sha256(
        np.ascontiguousarray(default_output).tobytes()
    ).hexdigest()
    candidate_tensor_sha = hashlib.sha256(
        np.ascontiguousarray(candidate_tensor).tobytes()
    ).hexdigest()
    if candidate_rows != rows or default_sha != rows[0] or not np.array_equal(
        default_output, candidate_tensor[0]
    ) or sidecar.get("candidate_tensor_sha256_before") != candidate_tensor_sha or (
        sidecar.get("candidate_tensor_sha256_after") != candidate_tensor_sha
    ):
        raise ValueError(
            "controlled snapshot candidate/default immutability tensors do not match SHAs"
        )
    if tuple(raw) != RAW_FEATURE_NAMES or tuple(source_complete) != RAW_FEATURE_NAMES:
        raise ValueError("controlled raw-context schema drifted")
    raw_values = _strict_json_numeric_array(
        [raw[name] for name in RAW_FEATURE_NAMES],
        (len(RAW_FEATURE_NAMES),),
        label="raw_context",
    )
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
    candidate_reasons = sidecar.get("candidate_reasons")
    sidecar_source_valid = sidecar.get("source_valid_mask")
    all_k_high_risk = sidecar.get("all_k_high_risk")
    default_output_sha256 = sidecar.get("default_output_sha256")
    candidate0_sha256 = sidecar.get("candidate0_sha256")
    default_candidate0_identity = sidecar.get("default_candidate0_identity")
    selected_index = sidecar.get("selected_index")
    scores = _strict_json_numeric_array(
        sidecar.get("scores"), (8,), label="selector scores"
    )
    if (
        not isinstance(physical, list)
        or len(physical) != 8
        or any(not isinstance(value, bool) for value in physical)
        or not isinstance(candidate_reasons, list)
        or len(candidate_reasons) != 8
        or any(
            not isinstance(row, list)
            or any(not isinstance(reason, str) for reason in row)
            for row in candidate_reasons
        )
        or not isinstance(sidecar_source_valid, list)
        or len(sidecar_source_valid) != 8
        or any(not isinstance(value, bool) for value in sidecar_source_valid)
        or sidecar_source_valid != valid
        or np.any(
            np.asarray(physical, dtype=np.bool_)
            & ~np.asarray(valid, dtype=np.bool_)
        )
        or type(all_k_high_risk) is not bool
        or all_k_high_risk
        is not bool(
            np.asarray(sidecar_source_valid, dtype=np.bool_).all()
            and not np.asarray(physical, dtype=np.bool_).any()
        )
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
        or sidecar.get("selected_trajectory_sha256") != rows[selected_index]
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
    semantic_clone_sha256 = case.get("canonical_semantic_clone_sha256")
    if semantic_clone_sha256 is not None and not _is_sha256(
        semantic_clone_sha256
    ):
        raise ValueError("controlled semantic clone SHA is invalid")
    controlled_signal_receipt = None
    controlled_signal_tensor_evidence = None
    controlled_model_input_cache_receipt = None
    source_class = case.get("signal_source_class")
    if source_class == "mapped_signal":
        chain = validate_mapped_signal_chain(case.get("mapped_signal_authority", {}))
        if controlled_scene_receipt is None:
            raise ValueError("controlled mapped-signal snapshot lacks same-tick receipt")
        signal = controlled_scene_receipt.get("signal")
        if not isinstance(signal, Mapping) or not isinstance(
            signal.get("tensor_evidence"), Mapping
        ):
            raise ValueError("controlled mapped-signal tick lacks tensor evidence")
        controlled_signal_tensor_evidence = dict(signal["tensor_evidence"])
        route_tensor, route_ids, map_tensor, map_ids = _signal_tensors_from_evidence(
            controlled_signal_tensor_evidence, tick_index=tick_index
        )
        controlled_signal_receipt = validate_mapped_signal_runtime_receipt(
            signal.get("source_receipt", {}),
            chain,
            route_tensor=route_tensor,
            route_lanelet_ids=route_ids,
            map_tensor=map_tensor,
            map_lanelet_ids=map_ids,
        )
        if (
            controlled_signal_receipt["current_phase"]
            != controlled_signal_tensor_evidence["current_phase"]
            or controlled_signal_receipt["decision_timestamp_s"]
            != controlled_signal_tensor_evidence["decision_timestamp_s"]
            or controlled_signal_receipt["source_timestamp_s"]
            != controlled_signal_tensor_evidence["source_timestamp_s"]
            or controlled_signal_receipt["route_signal_tensor_sha256"]
            != controlled_signal_tensor_evidence["route_signal_tensor_sha256"]
            or controlled_signal_receipt["map_signal_tensor_sha256"]
            != controlled_signal_tensor_evidence["map_signal_tensor_sha256"]
        ):
            raise ValueError("mapped signal receipt/tensor evidence binding drifted")
    causal_signal_atom_input = sidecar.get("causal_signal_atom_input")
    if source_class == "mapped_signal":
        if not isinstance(causal_signal_atom_input, Mapping):
            raise ValueError("controlled mapped-signal snapshot lacks causal stop-line input")
        validated_causal_signal = validate_mapped_signal_causal_atom_input(
            causal_signal_atom_input,
            chain,
            controlled_signal_receipt,
            route_tensor=route_tensor,
            route_lanelet_ids=route_ids,
            map_tensor=map_tensor,
            map_lanelet_ids=map_ids,
        )
    elif source_class == "no_signal":
        chain = validate_no_signal_chain(case.get("no_signal_authority", {}))
        if controlled_scene_receipt is None:
            raise ValueError("controlled non-signal snapshot lacks same-tick source receipt")
        signal = controlled_scene_receipt.get("signal")
        if not isinstance(signal, Mapping):
            raise ValueError("controlled non-signal tick lacks source receipt")
        controlled_signal_receipt = validate_runtime_no_signal_receipt(
            signal.get("source_receipt", {}), chain
        )
        if not isinstance(causal_signal_atom_input, Mapping):
            raise ValueError("controlled non-signal snapshot lacks causal source input")
        validated_causal_signal = validate_causal_signal_atom_input(
            causal_signal_atom_input, chain, controlled_signal_receipt
        )
    else:
        raise ValueError("controlled snapshot route-level source class is invalid")
    if controlled_scene_receipt is None or not isinstance(
        controlled_scene_receipt.get("model_input_cache"), Mapping
    ):
        raise ValueError("controlled snapshot lacks same-tick model-input cache receipt")
    controlled_model_input_cache_receipt = dict(
        controlled_scene_receipt["model_input_cache"]
    )
    cache_fields = {
        "schema_version",
        "scenario_id",
        "tick_index",
        "signal_source_class",
        "phase_authority_mode",
        "scene_map_tl_sha256",
        "model_cache_tl_sha256_before",
        "model_cache_tl_sha256_after",
        "model_route_lanes_tl_sha256",
        "cache_matches_scene_after",
        "observe_cache_unchanged",
        "sync_applied_before_tensor_conversion",
        "future_schedule_consumed",
        "phase_remaining_available",
    }
    if (
        set(controlled_model_input_cache_receipt) != cache_fields
        or controlled_model_input_cache_receipt.get("schema_version")
        != MODEL_INPUT_SIGNAL_CACHE_RECEIPT_SCHEMA_VERSION
        or controlled_model_input_cache_receipt.get("scenario_id")
        != case.get("scenario_id")
        or controlled_model_input_cache_receipt.get("tick_index") != tick_index
        or controlled_model_input_cache_receipt.get("signal_source_class")
        != source_class
        or controlled_model_input_cache_receipt.get("phase_authority_mode")
        != case.get("phase_authority_mode")
        or any(
            not _is_sha256(controlled_model_input_cache_receipt.get(field))
            for field in (
                "scene_map_tl_sha256",
                "model_cache_tl_sha256_before",
                "model_cache_tl_sha256_after",
                "model_route_lanes_tl_sha256",
            )
        )
        or controlled_model_input_cache_receipt.get("cache_matches_scene_after")
        is not True
        or controlled_model_input_cache_receipt.get(
            "sync_applied_before_tensor_conversion"
        )
        is not True
        or controlled_model_input_cache_receipt.get("future_schedule_consumed")
        is not False
        or controlled_model_input_cache_receipt.get("phase_remaining_available")
        is not False
        or (
            case.get("phase_authority_mode")
            != "controlled_same_tick_override"
            and controlled_model_input_cache_receipt.get("observe_cache_unchanged")
            is not True
        )
        or controlled_model_input_cache_receipt.get("model_cache_tl_sha256_after")
        != controlled_model_input_cache_receipt.get("scene_map_tl_sha256")
    ):
        raise ValueError("controlled model-input cache receipt contract drifted")
    source_artifact_root = case.get("route_signal_source_artifact_root_sha256")
    source_row_sha256 = case.get("route_signal_source_row_sha256")
    if not _is_sha256(source_artifact_root) or not _is_sha256(source_row_sha256):
        raise ValueError("controlled route-source row binding is unavailable")
    if semantic_clone_sha256 is not None:
        signal_applicable = validated_causal_signal["current_phase"] == "red"
        signal_columns = np.asarray([10, 12])
        if (
            not np.array_equal(
                atom_applicable[:, signal_columns],
                np.full((8, 2), signal_applicable, dtype=np.bool_),
            )
            or (
                not signal_applicable
                and not np.array_equal(atoms[:, signal_columns], np.zeros((8, 2)))
            )
            or not np.allclose(
                atoms[:, 12],
                compute_authorized_red_stopping_margin_costs(
                    candidate_tensor, validated_causal_signal, 0.1
                ),
                rtol=0.0,
                atol=1e-12,
            )
        ):
            raise ValueError("controlled signal atom source/applicability binding failed")
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "feature_payload": {
            "atom_matrix": atoms.tolist(),
            "source_valid_mask": list(valid),
            "atom_source_valid_mask": atom_source_valid.tolist(),
            "atom_applicable_mask": atom_applicable.tolist(),
            "physical_feasible_mask": list(physical),
            "candidate_row_sha256": list(rows),
            "candidate_tensor": candidate_tensor.tolist(),
            "default_output": default_output.tolist(),
            "causal_evidence": json.loads(json.dumps(causal_evidence, allow_nan=False)),
            "raw_context": {name: float(raw[name]) for name in RAW_FEATURE_NAMES},
            "context_source_complete": {
                name: bool(source_complete[name]) for name in RAW_FEATURE_NAMES
            },
        },
        "sidecar": {
            "tick_index": int(tick_index),
            "dt_s": 0.1,
            "scenario_id": str(case["scenario_id"]),
            "family": str(case["family"]),
            "tier": str(case["tier"]),
            "parameter_block_id": str(case["parameter_block_id"]),
            "route_identity_sha256": str(case["route_identity_sha256"]),
            "corridor_group_sha256": str(case["corridor_group_sha256"]),
            "map_family_id": str(case["map_family_id"]),
            "source_map_sha256": str(case["source_map_sha256"]),
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
            "causal_evidence_sha256": causal_sha,
            "route_lanes_sha256": str(sidecar["route_lanes_sha256"]),
            "route_lanes_speed_limit_sha256": str(
                sidecar["route_lanes_speed_limit_sha256"]
            ),
            "route_lanes_has_speed_limit_sha256": str(
                sidecar["route_lanes_has_speed_limit_sha256"]
            ),
            "physical_feasible_mask": list(physical),
            "source_valid_mask": list(sidecar_source_valid),
            "all_k_high_risk": all_k_high_risk,
            "selected_index": int(selected_index),
            "selected_trajectory_sha256": str(
                sidecar["selected_trajectory_sha256"]
            ),
            "score_contract": str(sidecar["score_contract"]),
            "tie_break_contract": str(sidecar["tie_break_contract"]),
            "normalized_atom_matrix_sha256": str(
                sidecar["normalized_atom_matrix_sha256"]
            ),
            "context_schema_version": CONTEXT_SCHEMA_VERSION,
            "context_source_receipt": dict(source_receipt),
            "generation_behavior_scale_sha256": _file_sha256(
                CORRECTED_GENERATION_SCALES
            ),
            "canonical_semantic_clone_sha256": semantic_clone_sha256,
            "route_signal_source_artifact_root_sha256": source_artifact_root,
            "route_signal_source_row_sha256": source_row_sha256,
            "signal_source_class": source_class,
            "phase_authority_mode": case.get("phase_authority_mode"),
            "controlled_signal_source_receipt": controlled_signal_receipt,
            "controlled_signal_tensor_evidence": controlled_signal_tensor_evidence,
            "controlled_model_input_cache_receipt": (
                controlled_model_input_cache_receipt
            ),
            "causal_signal_atom_input": causal_signal_atom_input,
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
    return canonical_json_bytes(payload)


def _canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _write_content_addressed_snapshot(
    *,
    output_dir: Path,
    index_file: Any,
    scenario_id: str,
    tick_index: int,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Write one snapshot using the sole frozen V25 canonical byte contract."""
    if not isinstance(scenario_id, str) or not scenario_id:
        raise ValueError("snapshot scenario_id must be a nonempty string")
    if (
        isinstance(tick_index, bool)
        or not isinstance(tick_index, int)
        or tick_index < 0
    ):
        raise ValueError("snapshot tick_index must be a nonnegative integer")
    if type(payload) is not dict or type(payload.get("feature_payload")) is not dict:
        raise ValueError("snapshot payload must contain a feature mapping")
    feature = payload["feature_payload"]
    causal_evidence = feature.get("causal_evidence")
    feature["causal_evidence"] = externalize_causal_evidence(
        output_dir=output_dir,
        causal_evidence=causal_evidence,
    )
    data = encode_snapshot(payload)
    digest = hashlib.sha256(data).hexdigest()
    relative = Path("snapshots") / f"{digest}{SNAPSHOT_SUFFIX}"
    target = output_dir / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() != data:
        raise ValueError("content-addressed snapshot collision")
    if not target.exists():
        target.write_bytes(data)
    row = {
        "scenario_id": scenario_id,
        "tick_index": tick_index,
        "relative_path": relative.as_posix(),
        "sha256": digest,
    }
    index_file.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    return row


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
