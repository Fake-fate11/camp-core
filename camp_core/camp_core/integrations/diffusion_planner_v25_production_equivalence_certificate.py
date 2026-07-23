from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any, Mapping

from .diffusion_planner_v25_actual_native_receipt_contract import (
    actual_native_receipt_contract_sha256,
)
from .diffusion_planner_v25_holdout_contract import canonical_sha256


SCHEMA_VERSION = (
    "camp_dp_v25_nonfresh_production_equivalence_certificate_v2"
)
STATUS = "passed_nonfresh_production_equivalence_certificate"
CHAIN_ROLES = frozenset(
    {
        "authority",
        "authority_review",
        "controller",
        "opening_release",
        "execution",
        "execution_review",
        "evaluation",
        "evaluation_review",
        "focused_tests",
    }
)
PRODUCTION_ENTRYPOINTS = [
    "scripts/integrations/create_diffusion_planner_v25_holdout_opening.py",
    "scripts/integrations/run_diffusion_planner_v25_holdout_execution.py",
    "scripts/integrations/review_diffusion_planner_v25_holdout_execution.py",
    "scripts/integrations/evaluate_diffusion_planner_v25_holdout.py",
    "scripts/integrations/review_diffusion_planner_v25_holdout_evaluation.py",
]
BRANCH_RECEIPT_COUNTS = {
    "candidate0_primary": 192,
    "candidate0_supplementary": 192,
    "scene14d": 192,
    "static14d": 192,
}
MUTATION_COVERAGE = [
    "branch_swap",
    "bool_integer_smuggling",
    "cross_branch_relation",
    "extra_field",
    "missing_required_field",
    "native_type",
    "nested_schema",
    "shape",
]
STATE_MACHINE_COVERAGE = [
    "artifact_fatal",
    "concurrent_reservation",
    "post_exposure_crash",
    "pre_exposure_retry_same_protocol",
    "pre_exposure_retry_wrong_protocol",
    "scientific_terminal_failure",
    "scientific_terminal_success",
    "typed_capability_failure",
]
FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "implementation_head",
        "critical_implementation_manifest_sha256",
        "actual_native_receipt_contract_sha256",
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "scenario_classes",
        "paired_unit_count",
        "arm_run_count",
        "tick_count",
        "sealed_chain",
        "production_entrypoints",
        "branch_receipt_counts",
        "mutation_coverage",
        "state_machine_coverage",
        "raw_native_receipt_ordering",
        "fresh_rows_or_outcomes_used",
        "certificate_payload_sha256",
    }
)


def freeze_production_equivalence_certificate(
    *,
    implementation_head: str,
    manifest_sha256: str,
    holdout_identity_sha256: str,
    experiment_protocol_sha256: str,
    sealed_chain: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "implementation_head": implementation_head,
        "critical_implementation_manifest_sha256": manifest_sha256,
        "actual_native_receipt_contract_sha256": (
            actual_native_receipt_contract_sha256()
        ),
        "holdout_identity_sha256": holdout_identity_sha256,
        "experiment_protocol_sha256": experiment_protocol_sha256,
        "scenario_classes": [
            "mapped_controlled_override",
            "mapped_observe",
            "no_signal",
        ],
        "paired_unit_count": 3,
        "arm_run_count": 9,
        "tick_count": 576,
        "sealed_chain": {
            role: _binding(binding, role)
            for role, binding in sorted(sealed_chain.items())
        },
        "production_entrypoints": list(PRODUCTION_ENTRYPOINTS),
        "branch_receipt_counts": dict(BRANCH_RECEIPT_COUNTS),
        "mutation_coverage": list(MUTATION_COVERAGE),
        "state_machine_coverage": list(STATE_MACHINE_COVERAGE),
        "raw_native_receipt_ordering": (
            "persisted_and_reopened_before_projection_or_comparison"
        ),
        "fresh_rows_or_outcomes_used": False,
    }
    result["certificate_payload_sha256"] = canonical_sha256(result)
    return validate_production_equivalence_certificate(
        result,
        implementation_head=implementation_head,
        manifest_sha256=manifest_sha256,
    )


def validate_production_equivalence_certificate(
    value: Mapping[str, Any],
    *,
    implementation_head: str,
    manifest_sha256: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != FIELDS:
        raise ValueError("production-equivalence certificate field set drifted")
    payload = dict(value)
    stored = payload.pop("certificate_payload_sha256")
    if (
        stored != canonical_sha256(payload)
        or value["schema_version"] != SCHEMA_VERSION
        or value["status"] != STATUS
        or value["implementation_head"] != implementation_head
        or value["critical_implementation_manifest_sha256"] != manifest_sha256
        or value["actual_native_receipt_contract_sha256"]
        != actual_native_receipt_contract_sha256()
        or not _sha(value["holdout_identity_sha256"])
        or not _sha(value["experiment_protocol_sha256"])
        or value["scenario_classes"]
        != ["mapped_controlled_override", "mapped_observe", "no_signal"]
        or value["paired_unit_count"] != 3
        or value["arm_run_count"] != 9
        or value["tick_count"] != 576
        or set(value["sealed_chain"]) != CHAIN_ROLES
        or any(
            _binding(binding, role) != binding
            for role, binding in value["sealed_chain"].items()
        )
        or value["production_entrypoints"] != PRODUCTION_ENTRYPOINTS
        or value["branch_receipt_counts"] != BRANCH_RECEIPT_COUNTS
        or value["mutation_coverage"] != MUTATION_COVERAGE
        or value["state_machine_coverage"] != STATE_MACHINE_COVERAGE
        or value["raw_native_receipt_ordering"]
        != "persisted_and_reopened_before_projection_or_comparison"
        or value["fresh_rows_or_outcomes_used"] is not False
    ):
        raise ValueError("production-equivalence certificate drifted")
    return json.loads(json.dumps(value))


def _binding(value: Mapping[str, Any], role: str) -> dict[str, str]:
    if type(value) is not dict or set(value) != {"path", "root_sha256"}:
        raise ValueError(f"production-equivalence {role} binding drifted")
    path = value["path"]
    if (
        type(path) is not str
        or not path.startswith("/root/autodl-tmp/")
        or not PurePosixPath(path).is_absolute()
        or not _sha(value["root_sha256"])
    ):
        raise ValueError(f"production-equivalence {role} binding drifted")
    return {"path": path, "root_sha256": value["root_sha256"]}


def _sha(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and not (set(value) - set("0123456789abcdef"))
    )
