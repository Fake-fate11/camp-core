from __future__ import annotations

from typing import Any, Mapping


SCHEMA_VERSION = "camp_dp_v25_evaluation_dual_head_provenance_v1"
FIELDS = frozenset(
    {
        "schema_version",
        "execution_implementation_head",
        "execution_critical_implementation_manifest_sha256",
        "opening_release_root_sha256",
        "scientific_exposure_ledger_sha256",
        "execution_root_sha256",
        "execution_review_root_sha256",
        "evaluation_implementation_head",
        "evaluation_critical_implementation_manifest_sha256",
    }
)


def freeze_evaluation_dual_head_provenance(
    *,
    execution_implementation_head: str,
    execution_critical_implementation_manifest_sha256: str,
    opening_release_root_sha256: str,
    scientific_exposure_ledger_sha256: str,
    execution_root_sha256: str,
    execution_review_root_sha256: str,
    evaluation_implementation_head: str,
    evaluation_critical_implementation_manifest_sha256: str,
) -> dict[str, str]:
    value = {
        "schema_version": SCHEMA_VERSION,
        "execution_implementation_head": execution_implementation_head,
        "execution_critical_implementation_manifest_sha256": (
            execution_critical_implementation_manifest_sha256
        ),
        "opening_release_root_sha256": opening_release_root_sha256,
        "scientific_exposure_ledger_sha256": (
            scientific_exposure_ledger_sha256
        ),
        "execution_root_sha256": execution_root_sha256,
        "execution_review_root_sha256": execution_review_root_sha256,
        "evaluation_implementation_head": evaluation_implementation_head,
        "evaluation_critical_implementation_manifest_sha256": (
            evaluation_critical_implementation_manifest_sha256
        ),
    }
    return validate_evaluation_dual_head_provenance(value)


def validate_evaluation_dual_head_provenance(
    value: Mapping[str, Any],
) -> dict[str, str]:
    if type(value) is not dict or set(value) != FIELDS:
        raise ValueError("evaluation dual-HEAD provenance field set drifted")
    result = dict(value)
    if result["schema_version"] != SCHEMA_VERSION:
        raise ValueError("evaluation dual-HEAD provenance schema drifted")
    for name in (
        "execution_implementation_head",
        "evaluation_implementation_head",
    ):
        if not _hex(result[name], 40):
            raise ValueError(f"evaluation dual-HEAD {name} drifted")
    for name in FIELDS - {
        "schema_version",
        "execution_implementation_head",
        "evaluation_implementation_head",
    }:
        if not _hex(result[name], 64):
            raise ValueError(f"evaluation dual-HEAD {name} drifted")
    return result


def _hex(value: Any, length: int) -> bool:
    return (
        type(value) is str
        and len(value) == length
        and not (set(value) - set("0123456789abcdef"))
    )
