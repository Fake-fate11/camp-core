"""Frozen contract for the V25 industrial-v3 bounded nonholdout attempt.

This module is outcome independent.  It defines the one-route, three-arm
compute-matched architecture, the pre-execution propagation matrix, the shared
per-tick latent manifest, full-denominator accounting, and the bounded
single-cluster no-claim evaluation topology.
"""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations.diffusion_planner_v21_native import (
    array_sha256,
    candidate_latents,
)
from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_contract_v3 import (
    evaluation_contract_v3,
)


SCHEMA_VERSION = "camp_dp_v25_industrial_v3_bounded_nonholdout_closed_loop_v1"
AUTHORITY_SHA256 = (
    "5e55899b63b8b9897d4bce65c19075784a6c560a509d892c8d156d13f7ef420e"
)
BASE_HEAD = "a8b665a019662afbc1f3dffedeb21ca74c543fa5"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
ROUTE_SHA256 = "63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd"
GENERATOR_NAME = "new_single_invocation_batched_k8_candidate_pool"
ARMS = ("pool_matched_candidate0", "Static14D", "Scene14D")
TICKS_PER_ARM = 64
PLANNED_TICKS = 192
SIMPLEX_NONNEGATIVE_ATOL = 1e-9
LOCAL_INTERPRETER = (
    r"C:\Users\lenovo\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\python\python.exe"
)
AUTODL_INTERPRETER = "/root/autodl-tmp/dp312_venv/bin/python"

UPSTREAM_ROOTS = {
    "industrial_contract": (
        "908fe1d57014e4932f71462d6d7e73ec58390f3296b3018df38092e4c0b128cb"
    ),
    "industrial_contract_review": (
        "23bb07ac537f9d53f7a2860b2314f55da4e2d468590d002c6cf25733f5e48556"
    ),
    "industrial_capability": (
        "fbcc8ab194520534c3b4986cccaf3d9a073b2cf975b6e3f006f61abe7791f20d"
    ),
    "industrial_capability_review": (
        "f32cb19b2c7bbd64e290f07a270f3e43462d31c86dc130a0c23a8b6eb363eec3"
    ),
    "generator_raw": (
        "731a715a0422f92e115bc078900d84c47b9f51f47c64181c3b8e71569cffdda4"
    ),
    "generator_raw_review": (
        "c0e24bb60a4eb9694bfda099d4d6d9b9be07f85fb486577275f0b32178cfbfc8"
    ),
    "generator_threshold": (
        "a4f6c54cb46378119b261fe0ef19f83f8b92d18fa3be3e02693f7905f3f8ac89"
    ),
    "generator_threshold_review": (
        "8882f0fa66d1690460662848fa67673657926cc663b0edf476866e1418034e0e"
    ),
    "selector_replay": (
        "9e89135981ace29e86ec6b0b270d17aad4ac089d8fbdec10d98a0aa14c3a0982"
    ),
    "selector_replay_review": (
        "3d2ac16d055f9957941d0d84b0b47282413a41559e47e67ce9a644ae8e3bc80b"
    ),
    "training": (
        "8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9"
    ),
    "training_review": (
        "ef2e9748a9ba0fff5b35f010cba6efd1b16d8e1dc0d562f5a7960c8dcb3d9be9"
    ),
}
ATOM_SCALES_SHA256 = (
    "72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb"
)

EXACT_DIRS = {
    "contract": "/root/autodl-tmp/camp_dp_v25_industrial_v3_bounded_closed_loop_contract_a8b665a0_5e55899b",
    "contract_review": "/root/autodl-tmp/camp_dp_v25_industrial_v3_bounded_closed_loop_contract_review_a8b665a0_5e55899b",
    "matrix": "/root/autodl-tmp/camp_dp_v25_industrial_v3_production_hardening_matrix_a8b665a0_5e55899b",
    "matrix_review": "/root/autodl-tmp/camp_dp_v25_industrial_v3_production_hardening_matrix_review_a8b665a0_5e55899b",
    "focused": "/root/autodl-tmp/camp_dp_v25_industrial_v3_production_hardening_focused_a8b665a0_5e55899b",
    "preflight": "/root/autodl-tmp/camp_dp_v25_industrial_v3_bounded_closed_loop_preflight_a8b665a0_5e55899b",
    "preflight_review": "/root/autodl-tmp/camp_dp_v25_industrial_v3_bounded_closed_loop_preflight_review_a8b665a0_5e55899b",
    "execution": "/root/autodl-tmp/camp_dp_v25_industrial_v3_bounded_closed_loop_execution_a8b665a0_5e55899b",
    "execution_review": "/root/autodl-tmp/camp_dp_v25_industrial_v3_bounded_closed_loop_execution_review_a8b665a0_5e55899b",
    "evaluation": "/root/autodl-tmp/camp_dp_v25_industrial_v3_bounded_closed_loop_evaluation_a8b665a0_5e55899b",
    "evaluation_review": "/root/autodl-tmp/camp_dp_v25_industrial_v3_bounded_closed_loop_evaluation_review_a8b665a0_5e55899b",
    "final_docs": "/root/autodl-tmp/camp_dp_v25_industrial_v3_bounded_closed_loop_final_docs_focused_a8b665a0_5e55899b",
}

PARAMETER_NAMES = (
    "interpreter",
    "schema_and_version_dispatch",
    "simplex_nonnegative_tolerance",
    "atom_scales",
    "static14d_weights",
    "scene14d_theta_and_context_policy",
    "atom_source_and_applicability",
    "physical_eligibility_mask",
    "tie_and_lowest_index",
    "terminal_and_failure_retention",
    "full_denominator",
    "latency_namespaces",
    "camp_head",
    "fixed_dp_head",
    "model_and_checkpoint",
    "route",
    "latent_policy",
    "artifact_seal_and_atomic_replace",
)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _parameter_rows() -> list[dict[str, Any]]:
    common = {
        "receipt": "typed per-tick receipt plus sealed inventory",
        "producer_validation": "required keyword or explicit assertion; no fallback",
        "execution_reviewer": "reviewer-local literal reconstruction",
        "evaluator": "industrial-v3 leaf source binding",
        "evaluation_reviewer": "reviewer-local leaf formula and source reconstruction",
    }
    rows = {
        "interpreter": (
            "entrypoint sys.executable/sys.version_info/sys.prefix/import receipt",
            "all V25 wrapper entrypoints",
            "exact local Codex runtime or AutoDL dp312 venv",
        ),
        "schema_and_version_dispatch": (
            "this contract schema and industrial-v3 schema",
            "contract/preflight/runner/evaluator dispatch",
            "exact version only; legacy dispatch rejected",
        ),
        "simplex_nonnegative_tolerance": (
            "camp_core.integrations.diffusion_planner_v25_scene_runtime.TRAINED_SIMPLEX_NONNEGATIVE_ATOL",
            "_FairPredictBatch._evaluate_pool Static14D and Scene14D select_candidate",
            "required simplex_nonnegative_atol=1e-9",
        ),
        "atom_scales": (
            "sealed training atom_scales.npy SHA256",
            "load_v25_runtime_selector_assets -> select_candidate",
            "finite positive float64[14] exact SHA",
        ),
        "static14d_weights": (
            "sealed training Static14D weight archive",
            "load_v25_runtime_selector_assets -> Static14D select_candidate",
            "finite simplex float64[14] exact SHA",
        ),
        "scene14d_theta_and_context_policy": (
            "sealed training Scene14D no-V2I archive/Theta/context schema",
            "build_v25_raw_context -> scene14d_weight_provider -> select_candidate",
            "no-V2I causal context and exact archive SHA",
        ),
        "atom_source_and_applicability": (
            "canonical 14D causal atom contract",
            "materialize_canonical_14d",
            "all source/applicability receipts retained",
        ),
        "physical_eligibility_mask": (
            "canonical physical/source validity masks",
            "select_candidate eligibility_mask_name=source_valid_mask",
            "strict bool[8], no empty fallback",
        ),
        "tie_and_lowest_index": (
            "production selector tie contract",
            "np.argmin on masked scores",
            "exact tie set and lowest eligible index",
        ),
        "terminal_and_failure_retention": (
            "bounded runner typed terminal contract",
            "three production arm run loops",
            "complete+failed+unattempted=64 per arm",
        ),
        "full_denominator": (
            "authority arms/ticks",
            "runner, execution review, evaluator",
            "3*64=192, no drop/replace/complete-case",
        ),
        "latency_namespaces": (
            "bounded latency schema",
            "pool/atoms/context/weights/selector/end-to-end receipt",
            "baseline CAMP stages n/a, never numeric zero",
        ),
        "camp_head": (
            "git HEAD and tracked-clean receipt",
            "preflight and all artifacts",
            "accepted implementation ancestry and pointer binding",
        ),
        "fixed_dp_head": (
            "fixed DP git HEAD and tracked-clean receipt",
            "preflight and model loader",
            FIXED_DP_HEAD,
        ),
        "model_and_checkpoint": (
            "root-bound probe config model args/checkpoint SHAs",
            "fixed-DP loader and per-tick forward receipt",
            "exact source/model/checkpoint/runtime fingerprints",
        ),
        "route": (
            "root-bound nonholdout route asset",
            "native route loader and every arm receipt",
            ROUTE_SHA256,
        ),
        "latent_policy": (
            "authority-derived per-tick canonical B8 manifest",
            "required latent_provider -> expanded same-ego input",
            "same tick exact bytes across arms; row0 zero; unique8",
        ),
        "artifact_seal_and_atomic_replace": (
            "diffusion_planner_artifact_seal",
            "all producer and reviewer artifact writers",
            "staging then os.replace; complete seal required",
        ),
    }
    return [
        {
            "parameter": name,
            "sealed_source": rows[name][0],
            "production_loader_and_callsite": rows[name][1],
            "frozen_value_or_rule": rows[name][2],
            **common,
        }
        for name in PARAMETER_NAMES
    ]


def contract() -> dict[str, Any]:
    industrial = evaluation_contract_v3()
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "frozen_outcome_independent_industrial_v3_bounded_nonholdout_contract",
        "authority_sha256": AUTHORITY_SHA256,
        "base_head": BASE_HEAD,
        "fixed_dp_head": FIXED_DP_HEAD,
        "upstream_roots": dict(UPSTREAM_ROOTS),
        "atom_scales_sha256": ATOM_SCALES_SHA256,
        "exact_dirs": dict(EXACT_DIRS),
        "architecture": {
            "generator": GENERATOR_NAME,
            "candidate_axis": "same_ego_expanded_batch_dimension_B_equals_8",
            "formal_model_calls_per_tick": 1,
            "sequential_model_calls": 0,
            "candidate0_rule": "immutable_pool_row0",
            "post_pool_model_dp_latent_candidate_generation_calls": 0,
            "arms": list(ARMS),
            "initial_state_equal": True,
            "post_divergence_cross_arm_input_or_pool_equality_claimed": False,
        },
        "source": {
            "route_sha256": ROUTE_SHA256,
            "development_nonholdout": True,
            "fresh_or_b4_outcome_read": False,
            "zero_overlap_levels": [
                "route",
                "state",
                "geometry",
                "source",
                "seed",
                "latent_instance",
            ],
            "zero_overlap_forbidden_authorities": [
                "Fresh_B2",
                "Fresh_B3",
                "Fresh_B4",
                "previously_used_development_input_only",
            ],
        },
        "latent_manifest": {
            "tick_count": TICKS_PER_ARM,
            "shape": [8, 321, 81, 4],
            "dtype": "float32",
            "row0_zero": True,
            "rows_unique": True,
            "same_tick_same_bytes_all_arms": True,
            "seed_formula": "uint32(sha256(authority_sha256|route_sha256|tick_ordinal)[:8])",
            "runtime_inputs_may_diverge": True,
        },
        "denominator": {
            "arm_runs": 3,
            "ticks_per_arm": TICKS_PER_ARM,
            "planned_ticks": PLANNED_TICKS,
            "per_arm_identity": list(ARMS),
            "per_arm_terminal_equation": "complete+failed+unattempted=64",
            "global_terminal_equation": "sum(all arm terminal classes)=192",
            "failure_retention": "typed_full_denominator_no_drop_replace_or_retry",
        },
        "latency": {
            "namespaces": [
                "pool_generation",
                "atoms",
                "context",
                "weights",
                "selector_pure_incremental",
                "end_to_end",
            ],
            "baseline_camp_stage_encoding": "not_applicable_null_not_numeric_zero",
            "baseline_pays_pool_cost": True,
            "operational_batch1_reference_separate": True,
        },
        "evaluation": {
            "industrial_contract_schema": industrial["schema_version"],
            "parent_endpoint_count": industrial["parent_endpoint_count"],
            "scalar_leaf_count": industrial["scalar_leaf_count"],
            "scalar_leaf_registry_sha256": canonical_sha256(
                industrial["scalar_leaf_registry"]
            ),
            "legacy_safetycost_role": "immutable_legacy_exploratory_diagnostic_only",
            "weighted_total_allowed": False,
            "independent_cluster_count": 1,
            "inferential_status": "not_evaluable_bounded_single_cluster",
            "ticks_candidates_or_arms_as_independent_n": False,
            "claim_authorized": False,
        },
        "pre_execution_hardening": {
            "required": True,
            "parameter_propagation_matrix": _parameter_rows(),
            "production_entrypoints_enumerated": True,
            "pass_and_typed_fail_end_to_end_dry_runs_required": True,
            "implicit_defaults_allowed": False,
            "residual_risk_classes": [
                "actually_executed_paths",
                "static_only_verified_paths",
                "unexecuted_paths",
            ],
            "zero_bug_claimed": False,
        },
        "interpreter": {
            "local": LOCAL_INTERPRETER,
            "autodl": AUTODL_INTERPRETER,
            "minimum_version": [3, 10],
            "bare_python_or_python3_allowed": False,
        },
        "prohibitions": {
            "training_or_retraining": False,
            "fresh_holdout_or_new_nonce": False,
            "old_artifact_or_cas_write": False,
            "dp_source_checkpoint_weights_theta_atoms_scales_change": False,
            "benefit_industrial_safety_production_deployment_claim": False,
        },
    }
    validate_contract(result)
    return result


def validate_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    candidate = copy.deepcopy(dict(value))
    expected = contract.__wrapped__() if hasattr(contract, "__wrapped__") else None
    # Avoid recursion: validate exact semantic invariants rather than rebuilding
    # through contract().
    if candidate.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("bounded contract schema drifted")
    if candidate.get("authority_sha256") != AUTHORITY_SHA256:
        raise ValueError("bounded authority drifted")
    if candidate.get("architecture", {}).get("arms") != list(ARMS):
        raise ValueError("bounded arm topology drifted")
    if candidate.get("denominator", {}).get("planned_ticks") != PLANNED_TICKS:
        raise ValueError("bounded denominator drifted")
    rows = candidate.get("pre_execution_hardening", {}).get(
        "parameter_propagation_matrix"
    )
    if (
        type(rows) is not list
        or [row.get("parameter") for row in rows] != list(PARAMETER_NAMES)
        or rows != _parameter_rows()
    ):
        raise ValueError("bounded propagation matrix drifted")
    if candidate.get("evaluation", {}).get("inferential_status") != (
        "not_evaluable_bounded_single_cluster"
    ):
        raise ValueError("bounded inference boundary drifted")
    if candidate.get("evaluation", {}).get("claim_authorized") is not False:
        raise ValueError("bounded claim boundary drifted")
    return candidate


def tick_latent_seed(tick_ordinal: int) -> int:
    if type(tick_ordinal) is not int or not 0 <= tick_ordinal < TICKS_PER_ARM:
        raise ValueError("tick ordinal must be int in [0,64)")
    digest = hashlib.sha256(
        f"{AUTHORITY_SHA256}|{ROUTE_SHA256}|{tick_ordinal}".encode("ascii")
    ).digest()
    return int.from_bytes(digest[:4], "big", signed=False)


def tick_latent(tick_ordinal: int) -> np.ndarray:
    value = np.asarray(
        candidate_latents(tick_latent_seed(tick_ordinal), noise_scale=1.0)
    )
    if (
        value.shape != (8, 321, 81, 4)
        or value.dtype != np.float32
        or not np.all(np.isfinite(value))
        or np.any(value[0] != 0.0)
        or len({array_sha256(row) for row in value}) != 8
    ):
        raise ValueError("bounded latent manifest row contract drifted")
    return value


def latent_manifest() -> list[dict[str, Any]]:
    rows = []
    for tick in range(TICKS_PER_ARM):
        value = tick_latent(tick)
        rows.append(
            {
                "tick_ordinal": tick,
                "seed_uint32": tick_latent_seed(tick),
                "shape": list(value.shape),
                "dtype": str(value.dtype),
                "tensor_sha256": array_sha256(value),
                "row_sha256": [array_sha256(row) for row in value],
                "row_unique_cardinality": 8,
                "row0_all_zero": True,
            }
        )
    return rows


def validate_terminal_accounting(arms: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(arms) != 3 or [row.get("arm") for row in arms] != list(ARMS):
        raise ValueError("bounded execution arm inventory drifted")
    global_total = 0
    normalized = []
    for row in arms:
        counts = {
            name: int(row.get(f"{name}_tick_count", -1))
            for name in ("complete", "failed", "unattempted")
        }
        if min(counts.values()) < 0 or sum(counts.values()) != TICKS_PER_ARM:
            raise ValueError("bounded per-arm terminal equation drifted")
        global_total += sum(counts.values())
        normalized.append({"arm": row["arm"], **counts})
    if global_total != PLANNED_TICKS:
        raise ValueError("bounded global denominator drifted")
    return {"arms": normalized, "planned_ticks": global_total}


def validate_latency_row(arm: str, value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "pool_generation",
        "atoms",
        "context",
        "weights",
        "selector_pure_incremental",
        "end_to_end",
    }
    if set(value) != expected:
        raise ValueError("bounded latency namespace drifted")
    result = dict(value)
    for key, item in result.items():
        if arm == "pool_matched_candidate0" and key in {
            "atoms",
            "context",
            "weights",
            "selector_pure_incremental",
        }:
            if item is not None:
                raise ValueError("baseline CAMP latency must be n/a/null")
        elif not isinstance(item, (int, float)) or not np.isfinite(float(item)):
            raise ValueError("called bounded latency stage must be finite")
    return result


def scalar_leaf_ids() -> list[str]:
    return [
        str(row["leaf_id"])
        for row in evaluation_contract_v3()["scalar_leaf_registry"]
    ]
