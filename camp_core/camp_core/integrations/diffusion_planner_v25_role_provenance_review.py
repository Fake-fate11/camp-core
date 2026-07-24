from __future__ import annotations

from typing import Any, Mapping


def independent_validate_evaluation_dual_head_provenance(
    value: Mapping[str, Any],
) -> dict[str, str]:
    fields = {
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
    if type(value) is not dict or set(value) != fields:
        raise ValueError("independent evaluation dual-HEAD field set drifted")
    result = dict(value)
    if result["schema_version"] != (
        "camp_dp_v25_evaluation_dual_head_provenance_v1"
    ):
        raise ValueError("independent evaluation dual-HEAD schema drifted")
    for name in (
        "execution_implementation_head",
        "evaluation_implementation_head",
    ):
        if not _hex(result[name], 40):
            raise ValueError(f"independent evaluation dual-HEAD {name} drifted")
    for name in fields - {
        "schema_version",
        "execution_implementation_head",
        "evaluation_implementation_head",
    }:
        if not _hex(result[name], 64):
            raise ValueError(f"independent evaluation dual-HEAD {name} drifted")
    return result


def independent_validate_evaluation_role_bindings(
    value: Mapping[str, Any],
    *,
    opening_release: Mapping[str, Any],
    execution_artifact_report: Mapping[str, Any],
    sealed_chain_roots: Mapping[str, Any],
    evaluation_implementation_head: str,
    evaluation_critical_implementation_manifest_sha256: str,
) -> dict[str, str]:
    provenance = independent_validate_evaluation_dual_head_provenance(value)
    if (
        type(opening_release) is not dict
        or type(execution_artifact_report) is not dict
        or type(sealed_chain_roots) is not dict
        or set(sealed_chain_roots)
        != {"opening_release", "execution", "execution_review"}
        or opening_release.get("implementation_source_head")
        != provenance["execution_implementation_head"]
        or opening_release.get("critical_implementation_manifest_sha256")
        != provenance[
            "execution_critical_implementation_manifest_sha256"
        ]
        or sealed_chain_roots["opening_release"]
        != provenance["opening_release_root_sha256"]
        or sealed_chain_roots["execution"]
        != provenance["execution_root_sha256"]
        or sealed_chain_roots["execution_review"]
        != provenance["execution_review_root_sha256"]
        or type(execution_artifact_report.get("opening_consumption"))
        is not dict
        or execution_artifact_report["opening_consumption"].get(
            "scientific_ledger_sha256"
        )
        != provenance["scientific_exposure_ledger_sha256"]
        or evaluation_implementation_head
        != provenance["evaluation_implementation_head"]
        or evaluation_critical_implementation_manifest_sha256
        != provenance[
            "evaluation_critical_implementation_manifest_sha256"
        ]
    ):
        raise ValueError(
            "independent evaluation dual-HEAD role binding drifted"
        )
    return provenance


def _hex(value: Any, length: int) -> bool:
    return (
        type(value) is str
        and len(value) == length
        and not (set(value) - set("0123456789abcdef"))
    )
