from __future__ import annotations

from typing import Any, Mapping

from .diffusion_planner_v25_b3_preopen import (
    SCHEMA_VERSION as B3_SCHEMA_VERSION,
    validate_b3_preopen_authority,
)
from .diffusion_planner_v25_b4_preopen import (
    SCHEMA_VERSION as B4_SCHEMA_VERSION,
    validate_production_equivalence_certificate,
    validate_b4_preopen_authority,
)
from .diffusion_planner_v25_holdout_preflight import (
    SCHEMA_VERSION as LEGACY_PREFLIGHT_SCHEMA_VERSION,
    validate_production_composition_preflight,
)
from .diffusion_planner_v25_production_equivalence_authority import (
    FILES as NONFRESH_CANARY_FILES,
    REVIEW_STATUS as NONFRESH_CANARY_REVIEW_STATUS,
    SCHEMA_VERSION as NONFRESH_CANARY_SCHEMA_VERSION,
    validate_nonfresh_production_equivalence_authority,
)
from .diffusion_planner_v25_holdout_plan_dispatch import (
    NONFRESH_CANARY_SPLIT,
)


def validate_holdout_preopen_authority(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("holdout preopen authority must be an object")
    schema = value.get("schema_version")
    if schema == B3_SCHEMA_VERSION:
        return validate_b3_preopen_authority(value)
    if schema == B4_SCHEMA_VERSION:
        return validate_b4_preopen_authority(value)
    if schema == NONFRESH_CANARY_SCHEMA_VERSION:
        return validate_nonfresh_production_equivalence_authority(value)
    raise ValueError("holdout preopen authority schema drifted")


def holdout_preopen_files(split: str) -> dict[str, str]:
    if split == NONFRESH_CANARY_SPLIT:
        return dict(NONFRESH_CANARY_FILES)
    if split not in {"fresh_b3", "fresh_b4"}:
        raise ValueError("holdout preopen split drifted")
    prefix = split
    return {
        "plan": f"{prefix}_execution_plan.json",
        "prepared_runtime": f"{prefix}_prepared_runtime_cases.json",
        "route_assets": f"{prefix}_route_assets.json",
        "map_suite": f"{prefix}_map_suite.json",
    }


def expected_holdout_preopen_review_status(split: str) -> str:
    if split == "fresh_b3":
        return "passed_independent_fresh_b3_preopen_review"
    if split == "fresh_b4":
        return "passed_independent_fresh_b4_preopen_review"
    if split == NONFRESH_CANARY_SPLIT:
        return NONFRESH_CANARY_REVIEW_STATUS
    raise ValueError("holdout preopen review split drifted")


def expected_holdout_zero_overlap_status(split: str) -> str:
    if split == "fresh_b3":
        return "passed_train_calibration_b2_b3_zero_overlap"
    if split == "fresh_b4":
        return "passed_train_calibration_b2_b3_b4_zero_overlap"
    if split == NONFRESH_CANARY_SPLIT:
        return "not_applicable_nonfresh_production_equivalence_fixture"
    raise ValueError("holdout zero-overlap split drifted")


def holdout_zero_overlap_passed(
    authority: Mapping[str, Any], *, split: str
) -> bool:
    if split == NONFRESH_CANARY_SPLIT:
        return (
            authority["nonfresh_provider_only"] is True
            and authority["real_b4_identity_or_rows_used"] is False
            and authority["fresh_identity_cas_created"] is False
            and authority["fresh_outcome_consumed"] is False
            and authority["outcome_fields_consumed"] == []
        )
    return (
        authority["zero_overlap"]["status"]
        == expected_holdout_zero_overlap_status(split)
    )


def validate_holdout_production_certificate(
    value: Mapping[str, Any],
    *,
    implementation_head: str,
    manifest_sha256: str,
) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("holdout production certificate must be an object")
    if value.get("schema_version") == LEGACY_PREFLIGHT_SCHEMA_VERSION:
        return validate_production_composition_preflight(value)
    return validate_production_equivalence_certificate(
        value,
        implementation_head=implementation_head,
        manifest_sha256=manifest_sha256,
    )
