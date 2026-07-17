"""Fail-closed machine authority for the V25 full-R preflight/execute gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any, Mapping

from camp_core.integrations.diffusion_planner_artifact_seal import (
    verify_complete_seal,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FORMAL_ROOT_SHA256 = (
    "c4dbd49c5fde36302046c6386ca1b8d9cdcaa922976f08230e6227962cc1e531"
)
A0_ROOT_SHA256 = (
    "b8664cd074bf48ded82017950616c851a3f3ca6afdd6fbe0ba0e705359e8ff41"
)
S01_PREFLIGHT_ROOT_SHA256 = (
    "bba8f0581efa688a4a85f193eed966f38501ac96de4883c493ab81caa1760451"
)
S01_REVIEW_ROOT_SHA256 = (
    "facfe0a1f4458e52ea2235197e7a2949537a1021c0d6fa69d5cf0018732f392d"
)
REJECTED_PARTIAL_ROOT_SHA256 = (
    "a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481"
)
A12_SUPERSEDED_ROOTS = frozenset(
    {
        "9735a52763e7ef61f516c65445d4f02057cf0fb0beda443354b07e6d69cbe54e",
        "76b21380fb66ffb2d90f6bd9adbccf887ea34458caf3383226ea8d17f6a1a833",
        "6e5847cf600048948e778330dd7aad3d7ea8aeb44f0e7e1070a83782114e87dd",
        "b705b826324a449eab87af36a1dd9325f3f773ebe6a3b14f8b437dc45478e7c8",
        "04d28ed769625f3db23ba2e9646384014817d4bb58196efae358ee2230677682",
        "1e84bf5bf35fa0dfea601b4e304b863cfabd0a5d3b1b8ee74e2cb7115c1f60cd",
        "27086204937a9501979bfcdb943be31f7e2be45d60bb7710508633e2af39bcfa",
        "1b2dd591e342fdfa0d88f05a2d2537bc8f51292d71502a22e701147cee15488c",
        "02529652c60e5843c2bb5568222291e5e3b5884fc218ab2e3cd0884810620ae4",
        "e2f7f484bdbb18d9eac7963cc7737cc6f39fc6427deb39e07a62060a9ecdc2a0",
        "c7375c3539727abf7b5a726b437bcb643de96fcbf2911b966bfa5e13f20881f8",
        "7d6308d5f3b36a3ec3925ffe1a3ef929f5e45940429e117b8fe52837a4e2f332",
        "50ae46bb76f76e07bac6a91405e30cade7bdfd715cf417a6e7d5931cdaaa3878",
        "c07e1c4cd63db8aaa21118925e7a78bbb2b6c1687ecbaf4939047057863979b1",
        "b92026ff87523e6d2be1fb583d99052eec628e1b8a39a18d4167d580be0f739f",
        "a692d57ee7d08b6cf563472e6cc98ec16a1f06babecd5da47bed715e3eba6cb9",
        "cd67c79c543dd9baad64e8042d103a91cd00ffd6b6877a42e9c718b6021e75a2",
        "bd460b74bf8b7040c719caf4b1d8226bc7d8f79b54c185c1a7efa6330d05871d",
        "4ec520d710a329a0ed728067d0251b744f03a24aa71c1d6e0d4ac7dfab2c0350",
        "de278472be78e6f6ebec087e36cdf87115047cfab0850213891054499165c105",
        "71a2be88ab93a8cc6406e20dac8f7eee90717456240fc4e44befb9965343c2a6",
        "baaf879f1eac5579a1029c2eb046dc125d8c82e7677f904b2b41dd8bfcd00947",
        "5d7ff800eb79a9d8cd1b6b91af0d9fb239d654c9661a65e3bdda83d69046d214",
        "ac557c902d9aa5069059e20072e3853f85a9c9f6a69f3b3d350d936bd0e1ab93",
        "1f2b042887bb9499f4af4b2c8cfff1000d0229988cde98cea91a8e7be54c9414",
        "9055042f5503e7b1e23067691d516e1933557dac7c3b5baf99bce893ea393069",
        "1afd6ccfe1dda380be1b3d912515cb112e8c315e1cf9a9a1e45bbbe069666106",
        "55ff4688dc4926348e26b8e9e161f4203c816eb8829dea974396f4f0aaa32b88",
    }
)
CANONICAL_JSON_BYTE_SPEC_VERSION = "camp_dp_v25_canonical_json_utf8_lf_v1"
PREFLIGHT_RELEASE_SCHEMA_VERSION = (
    "camp_dp_v25_ultra_full_config_preflight_release_v4"
)
EXECUTE_RELEASE_SCHEMA_VERSION = "camp_dp_v25_ultra_full_r_execute_release_v4"
ROOT_ROLES = (
    "a11_decision",
    "a11_ledger",
    "a11_validation",
    "r01_source",
    "r01_source_review",
    "r01_bounded",
    "r01_bounded_review",
)
EXPECTED_ROOT_STATUSES = {
    "a11_decision": "A1_5_R0_5_only_released",
    "a11_ledger": "passed_with_warnings_progress_source_valid_frozen",
    "a11_validation": "passed_with_warnings_progress_source_valid_frozen",
    "r01_source": "passed_source_only_full_r_closed",
    "r01_source_review": "passed_independent_source_review_full_r_closed",
    "r01_bounded": "passed_bounded_21red_1nosignal_x64_full_r_closed",
    "r01_bounded_review": (
        "passed_independent_21red_1nosignal_x64_review_full_r_closed"
    ),
}
ROOT_CONTRACTS = {
    "a11_decision": {
        "report_file": "decision.json",
        "schema_version": "camp_dp_v25_ultra_stage_a15_r05_decision_v6",
        "head_path": ("corrected_source_head",),
        "fields": frozenset(
            {
                "a0_root_sha256", "a1_5_authorized",
                "bounded_21red_1nosignal_x64_authorized_after_source_pass",
                "calibration_authorized", "candidate0_or_all_k_fallback_allowed",
                "corrected_source_head", "decision_date", "empty_source_valid",
                "fixed_dp_head", "formal_root_sha256", "fresh_b2_opened",
                "full_r_authorized", "monitor_authorized", "outcome_fields_consumed",
                "progress_formula", "progress_reference",
                "r0_5_source_authority_preflight_authorized", "rejected_roots",
                "s01_preflight_root_sha256", "s01_review_root_sha256",
                "scene_runtime_authorized", "schema_version", "selection_eligibility",
                "source_thread_id", "status", "superseded_diagnostic_roots",
                "training_authorized", "v2i_authorized",
            }
        ),
    },
    "a11_ledger": {
        "report_file": "atom_ledger.json",
        "schema_version": "camp_dp_v25_static_atom_ledger_v6",
        "head_path": ("authority", "stage_a_producer_head"),
        "fields": frozenset(
            {
                "atom_schema", "atoms", "authority", "dag_contract",
                "generation_scale_diagnostic", "ordered_schema_formula_payload",
                "ordered_schema_formula_sha256", "paper_9d_contract",
                "passive_latency_instrumentation", "progress_shortfall_decision",
                "r_red_scientific_coverage_freeze", "red_signal_contract",
                "schema_version", "source_state_enum", "stage", "stage_boundaries",
                "status", "training_scale_estimator_freeze",
            }
        ),
    },
    "a11_validation": {
        "report_file": "report.json",
        "schema_version": "camp_dp_v25_static_atom_ledger_validation_v6",
        "head_path": ("review_head",),
        "fields": frozenset(
            {
                "atom_count", "atom_results", "calibration_authorized",
                "contract_checks", "fail_count", "fresh_b2_opened",
                "independent_validator_imported_production_score_results",
                "kinematic_algebra", "numeric_recompute", "outcome_fields_consumed",
                "paper_9d_indices", "pass_count", "progress_adversarial",
                "progress_reference", "progress_reference_ultra_decision_required",
                "r_authorized", "review_head", "reviewed_artifact",
                "reviewed_root_sha256", "schema_version", "status",
                "training_authorized", "warn_count", "warning_atoms",
            }
        ),
    },
    "r01_source": {
        "report_file": "report.json",
        "schema_version": "camp_dp_v25_r01_authority_source_preflight_v4",
        "head_path": ("camp_head",),
        "fields": frozenset(
            {
                "a0_artifact", "a0_root_sha256", "a1_ledger_artifact",
                "a1_ledger_root_sha256", "a1_validation_artifact",
                "a1_validation_root_sha256", "all_source_chains_valid",
                "calibration_executed", "camp_head", "candidate_generation_started",
                "config_receipts_root_sha256", "distinct_source_map_count",
                "fixed_dp_head", "formal_executable_red_identity_count",
                "formal_root_sha256", "fresh_b2_opened", "full_r_authorized",
                "full_r_started", "model_loaded", "monitor_started",
                "non_signal_identity_count", "outcome_fields_consumed",
                "physical_signature_count", "physical_signature_sha256s",
                "red_by_tier", "rejected_roots", "s01_preflight_root_sha256",
                "s01_review_root_sha256", "scene_runtime_connected", "schema_version",
                "selected_bounded_probe_identity_count",
                "selected_bounded_probe_scenario_ids", "source_only", "status",
                "stop_line_geometry_sha256_count", "training_executed",
                "ultra_decision_artifact", "ultra_decision_root_sha256",
                "unique_regulatory_chain_count", "v2i_enabled",
                "validated_identity_chain_receipt_count",
            }
        ),
    },
    "r01_source_review": {
        "report_file": "report.json",
        "schema_version": "camp_dp_v25_r01_authority_source_review_v4",
        "head_path": ("review_head",),
        "fields": frozenset(
            {
                "bounded_probe_identity_count", "calibration_executed",
                "fixed_dp_head", "fresh_b2_opened", "full_r_authorized",
                "full_r_started", "independent_chain_checks",
                "independent_no_signal_regulatory_scan", "monitor_started",
                "outcome_fields_consumed", "producer_boolean_summary_trusted",
                "review_head", "reviewed_artifact", "reviewed_by_tier",
                "reviewed_distinct_source_map_count", "reviewed_non_signal_identity_count",
                "reviewed_red_identity_count", "reviewed_root_sha256", "schema_version",
                "status", "training_executed",
            }
        ),
    },
    "r01_bounded": {
        "report_file": "report.json",
        "schema_version": "camp_dp_v25_r01_21red_1nosignal_sequential_k8_preflight_v5",
        "head_path": ("camp_head",),
        "fields": frozenset(
            {
                "calibration_executed", "camp_head", "fixed_dp_head",
                "fresh_b2_opened", "full_r_authorized", "full_r_started",
                "monitor_started", "no_v2i", "non_signal_identity_count",
                "outcome_fields_consumed", "probe_count", "probe_fingerprint_roots",
                "probe_tick_count", "r0_review_artifact", "r0_review_root_sha256",
                "r0_source_artifact", "r0_source_root_sha256", "red_identity_count",
                "scene14d_runtime_connected", "schema_version", "selector_contract_sha256",
                "sequential_k8", "source_valid_progress_and_selection", "status",
                "tiers", "training_executed", "wall_seconds",
            }
        ),
    },
    "r01_bounded_review": {
        "report_file": "report.json",
        "schema_version": "camp_dp_v25_r01_21red_1nosignal_sequential_k8_review_v5",
        "head_path": ("review_head",),
        "fields": frozenset(
            {
                "actual_k8_default_context_hashes_independently_recomputed",
                "calibration_executed", "candidate0_operational_default_alias",
                "fixed_dp_head", "fresh_b2_opened", "full_r_authorized",
                "full_r_started", "independent_scalar_clip_affine_argmin",
                "monitor_started", "outcome_fields_consumed", "probe_count",
                "probe_tick_count", "probes", "r0_source_review_root_sha256",
                "r0_source_root_sha256", "review_head", "reviewed_artifact",
                "reviewed_root_sha256", "runtime_signal_receipts_independently_bound",
                "schema_version", "status", "training_executed",
            }
        ),
    },
}

ROOT_EXACT_VALUES: dict[str, dict[tuple[str, ...], Any]] = {
    "a11_decision": {
        ("decision_date",): "2026-07-18",
        ("source_thread_id",): "019f6eee-8fc2-75f3-843c-75562f610b13",
        ("fixed_dp_head",): FIXED_DP_HEAD,
        ("formal_root_sha256",): FORMAL_ROOT_SHA256,
        ("a0_root_sha256",): A0_ROOT_SHA256,
        ("s01_preflight_root_sha256",): S01_PREFLIGHT_ROOT_SHA256,
        ("s01_review_root_sha256",): S01_REVIEW_ROOT_SHA256,
        ("rejected_roots",): [REJECTED_PARTIAL_ROOT_SHA256],
        ("progress_reference",): "source_valid_candidate_set_reference",
        ("progress_formula",): (
            "r=max(progress[j] where source_valid[j]); "
            "progress_shortfall[k]=max(r-progress[k],0)"
        ),
        ("selection_eligibility",): "source_valid",
        ("empty_source_valid",): "fail_closed",
        ("candidate0_or_all_k_fallback_allowed",): False,
        ("a1_5_authorized",): True,
        ("r0_5_source_authority_preflight_authorized",): True,
        ("bounded_21red_1nosignal_x64_authorized_after_source_pass",): True,
        ("full_r_authorized",): False,
        ("monitor_authorized",): False,
        ("training_authorized",): False,
        ("calibration_authorized",): False,
        ("scene_runtime_authorized",): False,
        ("v2i_authorized",): False,
        ("fresh_b2_opened",): False,
        ("outcome_fields_consumed",): [],
    },
    "a11_ledger": {
        ("stage",): "A_static_atom_semantics",
        ("authority", "fixed_dp_head"): FIXED_DP_HEAD,
        ("authority", "formal_source_root_sha256"): FORMAL_ROOT_SHA256,
        ("authority", "a0_root_sha256"): A0_ROOT_SHA256,
        ("authority", "s01_preflight_root_sha256"): S01_PREFLIGHT_ROOT_SHA256,
        ("authority", "s01_review_root_sha256"): S01_REVIEW_ROOT_SHA256,
        ("authority", "rejected_roots"): [REJECTED_PARTIAL_ROOT_SHA256],
        ("progress_shortfall_decision", "reference"): (
            "source_valid_candidate_set_reference"
        ),
        ("stage_boundaries",): {
            "r_authorized": False,
            "full_corpus_started": False,
            "training_executed": False,
            "calibration_executed": False,
            "scene_runtime_connected": False,
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
        },
        (
            "passive_latency_instrumentation",
            "microbatch_cache_sharding_enabled",
        ): False,
        ("dag_contract", "training_calibration_fresh"): (
            "E1 -> T/E2 -> Q -> one-shot F -> E3; each Ultra-gated"
        ),
        ("dag_contract", "outcome_red_10m_heuristic_gate"): (
            "must be replaced or independently certified before calibration "
            "or Fresh B2 pre-open"
        ),
        (
            "red_signal_contract",
            "outcome_evaluator_10m_nearest_line_heuristic",
        ): (
            "calibration/Fresh B2 pre-open hard gate; not accepted as "
            "regulatory authority"
        ),
    },
    "a11_validation": {
        ("atom_count",): 14,
        ("pass_count",): 9,
        ("warn_count",): 5,
        ("fail_count",): 0,
        ("paper_9d_indices",): list(range(9)),
        ("progress_reference",): "source_valid_candidate_set_reference",
        ("progress_reference_ultra_decision_required",): False,
        ("independent_validator_imported_production_score_results",): False,
        ("r_authorized",): False,
        ("training_authorized",): False,
        ("calibration_authorized",): False,
        ("fresh_b2_opened",): False,
        ("outcome_fields_consumed",): [],
        ("contract_checks",): {
            "training_estimator_frozen": True,
            "red_coverage_fail_closed": True,
            "dag_c_d_gated": True,
            "progress_source_valid_frozen": True,
            "r_and_fresh_closed": True,
        },
    },
    "r01_source": {
        ("a0_root_sha256",): A0_ROOT_SHA256,
        ("formal_root_sha256",): FORMAL_ROOT_SHA256,
        ("s01_preflight_root_sha256",): S01_PREFLIGHT_ROOT_SHA256,
        ("s01_review_root_sha256",): S01_REVIEW_ROOT_SHA256,
        ("rejected_roots",): [REJECTED_PARTIAL_ROOT_SHA256],
        ("fixed_dp_head",): FIXED_DP_HEAD,
        ("all_source_chains_valid",): True,
        ("source_only",): True,
        ("candidate_generation_started",): False,
        ("model_loaded",): False,
        ("training_executed",): False,
        ("calibration_executed",): False,
        ("scene_runtime_connected",): False,
        ("v2i_enabled",): False,
        ("monitor_started",): False,
        ("full_r_authorized",): False,
        ("full_r_started",): False,
        ("fresh_b2_opened",): False,
        ("outcome_fields_consumed",): [],
        ("formal_executable_red_identity_count",): 21,
        ("validated_identity_chain_receipt_count",): 21,
        ("unique_regulatory_chain_count",): 21,
        ("distinct_source_map_count",): 4,
        ("physical_signature_count",): 9,
        ("stop_line_geometry_sha256_count",): 5,
        ("selected_bounded_probe_identity_count",): 22,
        ("non_signal_identity_count",): 1,
        ("red_by_tier",): {"borderline": 10, "easy": 6, "high_risk": 5},
    },
    "r01_source_review": {
        ("fixed_dp_head",): FIXED_DP_HEAD,
        ("producer_boolean_summary_trusted",): False,
        ("independent_no_signal_regulatory_scan",): True,
        ("training_executed",): False,
        ("calibration_executed",): False,
        ("monitor_started",): False,
        ("full_r_authorized",): False,
        ("full_r_started",): False,
        ("fresh_b2_opened",): False,
        ("outcome_fields_consumed",): [],
        ("reviewed_red_identity_count",): 21,
        ("reviewed_distinct_source_map_count",): 4,
        ("reviewed_non_signal_identity_count",): 1,
        ("bounded_probe_identity_count",): 22,
        ("reviewed_by_tier",): {
            "borderline": 10,
            "easy": 6,
            "high_risk": 5,
        },
    },
    "r01_bounded": {
        ("fixed_dp_head",): FIXED_DP_HEAD,
        ("sequential_k8",): True,
        ("no_v2i",): True,
        ("source_valid_progress_and_selection",): True,
        ("scene14d_runtime_connected",): False,
        ("training_executed",): False,
        ("calibration_executed",): False,
        ("monitor_started",): False,
        ("full_r_authorized",): False,
        ("full_r_started",): False,
        ("fresh_b2_opened",): False,
        ("outcome_fields_consumed",): [],
        ("probe_count",): 22,
        ("probe_tick_count",): 1408,
        ("red_identity_count",): 21,
        ("non_signal_identity_count",): 1,
        ("tiers",): [
            "borderline", "easy", "high_risk", "easy", "borderline",
            "borderline", "borderline", "easy", "borderline", "borderline",
            "borderline", "high_risk", "borderline", "easy", "high_risk",
            "high_risk", "high_risk", "easy", "borderline", "easy",
            "borderline", "easy",
        ],
    },
    "r01_bounded_review": {
        ("fixed_dp_head",): FIXED_DP_HEAD,
        ("actual_k8_default_context_hashes_independently_recomputed",): True,
        ("candidate0_operational_default_alias",): True,
        ("independent_scalar_clip_affine_argmin",): True,
        ("runtime_signal_receipts_independently_bound",): True,
        ("training_executed",): False,
        ("calibration_executed",): False,
        ("monitor_started",): False,
        ("full_r_authorized",): False,
        ("full_r_started",): False,
        ("fresh_b2_opened",): False,
        ("outcome_fields_consumed",): [],
        ("probe_count",): 22,
        ("probe_tick_count",): 1408,
    },
}


def _nested_value(payload: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = payload
    for key in path:
        if not isinstance(value, Mapping) or key not in value:
            raise ValueError(f"missing exact-value authority field: {'.'.join(path)}")
        value = value[key]
    return value


def strict_json_equal(actual: Any, expected: Any) -> bool:
    """Compare JSON values without Python's bool/int/float coercions."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            strict_json_equal(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            strict_json_equal(left, right)
            for left, right in zip(actual, expected)
        )
    if isinstance(expected, float):
        return expected == actual and actual not in (float("inf"), float("-inf"))
    return actual == expected


_LEDGER_AUTHORITY_FIELDS = frozenset(
    {
        "s01_source_head",
        "s01_release_baseline_head",
        "stage_a_producer_head",
        "fixed_dp_head",
        "s01_preflight_root_sha256",
        "s01_review_root_sha256",
        "formal_source_root_sha256",
        "a0_artifact",
        "a0_root_sha256",
        "ultra_decision_artifact",
        "ultra_decision_root_sha256",
        "plan_path",
        "plan_sha256",
        "rejected_roots",
    }
)
_LEDGER_STAGE_BOUNDARY_FIELDS = frozenset(
    {
        "r_authorized",
        "full_corpus_started",
        "training_executed",
        "calibration_executed",
        "scene_runtime_connected",
        "fresh_b2_opened",
        "outcome_fields_consumed",
    }
)
_VALIDATION_CONTRACT_CHECK_FIELDS = frozenset(
    {
        "training_estimator_frozen",
        "red_coverage_fail_closed",
        "dag_c_d_gated",
        "progress_source_valid_frozen",
        "r_and_fresh_closed",
    }
)
_NESTED_EXACT_KEYSETS = {
    ("a11_ledger", "authority"): _LEDGER_AUTHORITY_FIELDS,
    ("a11_ledger", "stage_boundaries"): _LEDGER_STAGE_BOUNDARY_FIELDS,
    ("a11_validation", "contract_checks"): _VALIDATION_CONTRACT_CHECK_FIELDS,
}
_ALLOWED_NESTED_CONTROL_PATHS = frozenset(
    {
        ("a11_ledger", "stage_boundaries", field)
        for field in _LEDGER_STAGE_BOUNDARY_FIELDS
    }
    | {
        (
            "a11_ledger",
            "passive_latency_instrumentation",
            "microbatch_cache_sharding_enabled",
        ),
        ("a11_ledger", "dag_contract", "training_calibration_fresh"),
        ("a11_ledger", "dag_contract", "outcome_red_10m_heuristic_gate"),
        (
            "a11_ledger",
            "red_signal_contract",
            "outcome_evaluator_10m_nearest_line_heuristic",
        ),
        ("a11_validation", "contract_checks", "r_and_fresh_closed"),
    }
)
_CONTROL_SUFFIXES_NORMALIZED = (
    "authorized",
    "executed",
    "started",
    "connected",
    "enabled",
)
_CONTROL_SUBSTRINGS_NORMALIZED = (
    "fresh",
    "outcome",
    "future",
    "holdout",
    "label",
    "idproxy",
    "identityproxy",
)


def _normalized_control_name(value: str) -> str:
    """Normalize snake/camel/hyphen spellings before control-field checks."""
    return "".join(character for character in value.lower() if character.isalnum())


def _verify_nested_control_schema(role: str, report: Mapping[str, Any]) -> None:
    for (key_role, field), expected_keys in _NESTED_EXACT_KEYSETS.items():
        if key_role != role:
            continue
        value = report.get(field)
        if not isinstance(value, Mapping) or set(value) != expected_keys:
            raise ValueError(f"{role}.{field} nested exact key set drifted")

    def visit(value: Any, path: tuple[str, ...]) -> None:
        if isinstance(value, Mapping):
            for raw_key, child in value.items():
                if type(raw_key) is not str:
                    raise ValueError(f"{role} contains a non-string JSON key")
                child_path = (*path, raw_key)
                normalized = _normalized_control_name(raw_key)
                is_control = (
                    normalized.endswith(_CONTROL_SUFFIXES_NORMALIZED)
                    or any(
                        token in normalized
                        for token in _CONTROL_SUBSTRINGS_NORMALIZED
                    )
                )
                if (
                    len(child_path) > 2
                    and is_control
                    and child_path not in _ALLOWED_NESTED_CONTROL_PATHS
                ):
                    raise ValueError(
                        f"{role} contains unregistered nested control field: "
                        + ".".join(child_path[1:])
                    )
                visit(child, child_path)
        elif isinstance(value, list):
            for child in value:
                visit(child, path)

    visit(report, (role,))


def _verify_root_exact_values(role: str, report: Mapping[str, Any]) -> None:
    for path, expected in ROOT_EXACT_VALUES[role].items():
        if not strict_json_equal(_nested_value(report, path), expected):
            raise ValueError(
                f"{role} exact-value authority drifted at {'.'.join(path)}"
            )
    _verify_nested_control_schema(role, report)

POINTER_ONLY_PATHS = frozenset(
    {
        "docs/diffusion_planner_current_status.md",
        "docs/diffusion_planner_v25_iteration_audit.md",
        "camp_core/tests/test_diffusion_planner_v25_iteration_audit.py",
    }
)
CRITICAL_IMPLEMENTATION_PATHS = (
    "camp_core/camp_core/integrations/diffusion_planner.py",
    "camp_core/camp_core/integrations/diffusion_planner_causal_atoms.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_context.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_semantic_authority.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_route_signal_authority.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_full_r_authority.py",
    "scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py",
    "scripts/integrations/run_diffusion_planner_v25_controlled_training_corpus.py",
    "scripts/integrations/preflight_diffusion_planner_v25_r0_red_k8.py",
    "scripts/integrations/review_diffusion_planner_v25_r0_red_k8.py",
    "scripts/integrations/review_diffusion_planner_v25_full_config_preflight.py",
    "scripts/integrations/review_diffusion_planner_v25_controlled_training_corpus.py",
    "scripts/integrations/preflight_diffusion_planner_v25_a16_r06_route_signal_source.py",
    "scripts/integrations/review_diffusion_planner_v25_a16_r06_route_signal_source.py",
    "configs/integrations/diffusion_planner_v25_atom_scales_correction_v2.json",
    "configs/integrations/diffusion_planner_v25_atom_ledger_plan_v6.json",
)
_SHA_CHARS = frozenset("0123456789abcdef")


def canonical_json_bytes(payload: Any) -> bytes:
    """Return the frozen V25 canonical JSON byte representation.

    The contract is UTF-8, sorted keys, non-ASCII preserved, compact
    separators, no NaN/Infinity, and exactly one trailing LF.
    """
    return (
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and not set(value) - _SHA_CHARS
    )


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"authority JSON is not an object: {path}")
    return value


def _safe_repo_path(value: Any) -> str:
    if type(value) is not str or not value or "\\" in value:
        raise ValueError("implementation manifest path is empty")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or value != pure.as_posix():
        raise ValueError("implementation manifest path is unsafe")
    return value


def build_critical_implementation_manifest(repo: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for relative in CRITICAL_IMPLEMENTATION_PATHS:
        path = repo / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"critical implementation file is unavailable: {relative}")
        manifest[relative] = file_sha256(path)
    return manifest


def verify_dual_head_contract(
    *,
    repo: Path,
    implementation_source_head: str,
    current_pointer_head: str,
    implementation_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        not isinstance(implementation_source_head, str)
        or len(implementation_source_head) != 40
        or not isinstance(current_pointer_head, str)
        or len(current_pointer_head) != 40
    ):
        raise ValueError("dual-HEAD values are invalid")
    expected_manifest = build_critical_implementation_manifest(repo)
    if (
        type(implementation_manifest) is not dict
        or set(implementation_manifest) != set(CRITICAL_IMPLEMENTATION_PATHS)
        or any(_safe_repo_path(key) != key for key in implementation_manifest)
        or any(not is_sha256(value) for value in implementation_manifest.values())
        or not strict_json_equal(implementation_manifest, expected_manifest)
    ):
        raise ValueError("critical implementation manifest drifted")
    changed: list[str] = []
    if implementation_source_head != current_pointer_head:
        completed = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                implementation_source_head,
                current_pointer_head,
                "--",
            ],
            cwd=repo,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        changed = [line.replace("\\", "/") for line in completed.stdout.splitlines()]
        if not changed or set(changed) - POINTER_ONLY_PATHS:
            raise ValueError("dual-HEAD diff exceeds the pointer/docs allowlist")
    return {
        "implementation_source_head": implementation_source_head,
        "current_pointer_head": current_pointer_head,
        "pointer_only_changed_paths": changed,
        "implementation_manifest_sha256": canonical_sha256(expected_manifest),
    }


def _parse_heads(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        if "=" not in line:
            raise ValueError(f"malformed HEADS line: {path}")
        key, value = line.split("=", 1)
        if not key or key in result or not value:
            raise ValueError(f"duplicate/empty HEADS field: {path}")
        result[key] = value
    if not result:
        raise ValueError(f"empty HEADS: {path}")
    return result


def verify_seven_root_chain(
    *,
    bindings: Mapping[str, Any],
    implementation_source_head: str,
    fixed_dp_head: str,
    rejected_root_sha256: str,
) -> dict[str, dict[str, Any]]:
    if fixed_dp_head != FIXED_DP_HEAD:
        raise ValueError("fixed DP authority drifted")
    if rejected_root_sha256 != REJECTED_PARTIAL_ROOT_SHA256:
        raise ValueError("rejected partial root authority drifted")
    if set(bindings) != set(ROOT_ROLES):
        raise ValueError("release does not bind the exact seven prerequisite roots")
    verified: dict[str, dict[str, Any]] = {}
    for role in ROOT_ROLES:
        binding = bindings[role]
        contract = ROOT_CONTRACTS[role]
        if not isinstance(binding, Mapping) or set(binding) != {
            "path",
            "root_sha256",
            "report_file",
        }:
            raise ValueError(f"{role} binding field set drifted")
        artifact = Path(str(binding["path"]))
        root = str(binding["root_sha256"])
        report_file = str(binding["report_file"])
        if (
            Path(report_file).name != report_file
            or report_file != contract["report_file"]
            or not is_sha256(root)
        ):
            raise ValueError(f"{role} binding is unsafe")
        seal = verify_complete_seal(artifact, root, label=f"V25 {role}")
        if (artifact / "run.exit").read_text(encoding="ascii") != "0\n":
            raise ValueError(f"{role} run.exit is not zero")
        report = _load_object(artifact / report_file)
        heads = _parse_heads(artifact / "HEADS")
        report_head: Any = report
        for key in contract["head_path"]:
            report_head = report_head.get(key) if isinstance(report_head, Mapping) else None
        report_fixed_dp = report.get("fixed_dp_head")
        if role == "a11_ledger":
            report_fixed_dp = report.get("authority", {}).get("fixed_dp_head")
        elif role == "a11_validation":
            report_fixed_dp = heads.get("fixed_dp_head")
        if (
            set(report) != contract["fields"]
            or report.get("schema_version") != contract["schema_version"]
            or report.get("status") != EXPECTED_ROOT_STATUSES[role]
            or heads
            != {
                "camp_head": implementation_source_head,
                "fixed_dp_head": fixed_dp_head,
            }
            or report_head != implementation_source_head
            or report_fixed_dp != fixed_dp_head
            or (
                "fresh_b2_opened" in report
                and report.get("fresh_b2_opened") is not False
            )
            or (
                "full_r_authorized" in report
                and report.get("full_r_authorized") is not False
            )
            or (
                "outcome_fields_consumed" in report
                and report.get("outcome_fields_consumed") != []
            )
        ):
            raise ValueError(f"{role} status/HEADS authority drifted")
        _verify_root_exact_values(role, report)
        verified[role] = {
            "path": str(artifact),
            "root_sha256": seal["root_sha256"],
            "report": report,
        }

    roots = {role: row["root_sha256"] for role, row in verified.items()}
    decision = verified["a11_decision"]["report"]
    ledger = verified["a11_ledger"]["report"]
    validation = verified["a11_validation"]["report"]
    source = verified["r01_source"]["report"]
    source_review = verified["r01_source_review"]["report"]
    bounded = verified["r01_bounded"]["report"]
    bounded_review = verified["r01_bounded_review"]["report"]
    paths = {role: Path(str(bindings[role]["path"])).resolve() for role in ROOT_ROLES}
    if (
        not A12_SUPERSEDED_ROOTS.issubset(
            set(decision.get("superseded_diagnostic_roots") or [])
        )
        or decision.get("formal_root_sha256") != source.get("formal_root_sha256")
        or decision.get("rejected_roots") != [rejected_root_sha256]
        or source.get("rejected_roots") != [rejected_root_sha256]
        or ledger.get("authority", {}).get("ultra_decision_root_sha256")
        != roots["a11_decision"]
        or Path(str(ledger.get("authority", {}).get("ultra_decision_artifact"))).resolve()
        != paths["a11_decision"]
        or validation.get("reviewed_root_sha256") != roots["a11_ledger"]
        or Path(str(validation.get("reviewed_artifact"))).resolve()
        != paths["a11_ledger"]
        or source.get("ultra_decision_root_sha256") != roots["a11_decision"]
        or Path(str(source.get("ultra_decision_artifact"))).resolve()
        != paths["a11_decision"]
        or source.get("a1_ledger_root_sha256") != roots["a11_ledger"]
        or Path(str(source.get("a1_ledger_artifact"))).resolve()
        != paths["a11_ledger"]
        or source.get("a1_validation_root_sha256") != roots["a11_validation"]
        or Path(str(source.get("a1_validation_artifact"))).resolve()
        != paths["a11_validation"]
        or source_review.get("reviewed_root_sha256") != roots["r01_source"]
        or Path(str(source_review.get("reviewed_artifact"))).resolve()
        != paths["r01_source"]
        or bounded.get("r0_source_root_sha256") != roots["r01_source"]
        or Path(str(bounded.get("r0_source_artifact"))).resolve()
        != paths["r01_source"]
        or bounded.get("r0_review_root_sha256") != roots["r01_source_review"]
        or Path(str(bounded.get("r0_review_artifact"))).resolve()
        != paths["r01_source_review"]
        or bounded_review.get("reviewed_root_sha256") != roots["r01_bounded"]
        or Path(str(bounded_review.get("reviewed_artifact"))).resolve()
        != paths["r01_bounded"]
        or bounded_review.get("r0_source_root_sha256") != roots["r01_source"]
        or bounded_review.get("r0_source_review_root_sha256")
        != roots["r01_source_review"]
    ):
        raise ValueError("seven-root cross-link authority drifted")
    return verified


def consume_one_shot_nonce(
    *,
    ledger_dir: Path,
    gate: str,
    nonce: str,
    authorized_output_dir: str,
    requested_output_dir: Path,
) -> Path:
    if gate not in {"preflight", "execute"} or type(nonce) is not str or not is_sha256(nonce):
        raise ValueError("one-shot gate/nonce is invalid")
    if type(authorized_output_dir) is not str or not authorized_output_dir:
        raise ValueError("authorized output directory must be a native string")
    expected_raw = Path(authorized_output_dir)
    expected = expected_raw.resolve()
    if not expected_raw.is_absolute() or authorized_output_dir != str(expected):
        raise ValueError("authorized output directory is not absolute canonical")
    requested = requested_output_dir.resolve()
    if requested != expected:
        raise ValueError("release is bound to a different exact output directory")
    ledger_dir.mkdir(parents=True, exist_ok=True)
    marker = ledger_dir / f"v25_{gate}_{nonce}.consumed.json"
    payload = {
        "gate": gate,
        "nonce": nonce,
        "authorized_output_dir": str(expected),
    }
    encoded = (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")
    try:
        with marker.open("xb") as handle:
            handle.write(encoded)
    except FileExistsError as exc:
        raise ValueError("release nonce was already consumed") from exc
    return marker
