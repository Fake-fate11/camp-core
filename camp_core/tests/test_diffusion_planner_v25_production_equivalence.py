from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
    canonical_sha256,
)
from camp_core.integrations.diffusion_planner_v25_production_equivalence_certificate import (
    freeze_production_equivalence_certificate,
    validate_production_equivalence_certificate,
)
from camp_core.integrations.diffusion_planner_v25_role_provenance_review import (
    independent_validate_evaluation_dual_head_provenance,
    independent_validate_evaluation_role_bindings,
)


HEAD = "1" * 40
SHA = "2" * 64
EXECUTION_HEAD = "e" * 40
EXECUTION_MANIFEST = "f" * 64
ROLES = (
    "authority",
    "authority_review",
    "controller",
    "opening_release",
    "execution",
    "execution_review",
    "evaluation",
    "evaluation_review",
    "focused_tests",
)


def _chain() -> dict[str, dict[str, str]]:
    return {
        role: {
            "path": f"/root/autodl-tmp/nonfresh_{role}",
            "root_sha256": f"{index + 5:x}" * 64,
        }
        for index, role in enumerate(ROLES)
    }


def _provenance() -> dict[str, str]:
    chain = _chain()
    return {
        "schema_version": "camp_dp_v25_evaluation_dual_head_provenance_v1",
        "execution_implementation_head": EXECUTION_HEAD,
        "execution_critical_implementation_manifest_sha256": (
            EXECUTION_MANIFEST
        ),
        "opening_release_root_sha256": chain["opening_release"][
            "root_sha256"
        ],
        "scientific_exposure_ledger_sha256": "0" * 64,
        "execution_root_sha256": chain["execution"]["root_sha256"],
        "execution_review_root_sha256": chain["execution_review"][
            "root_sha256"
        ],
        "evaluation_implementation_head": HEAD,
        "evaluation_critical_implementation_manifest_sha256": SHA,
    }


def _certificate() -> dict:
    return freeze_production_equivalence_certificate(
        implementation_head=HEAD,
        manifest_sha256=SHA,
        holdout_identity_sha256="3" * 64,
        experiment_protocol_sha256="4" * 64,
        dual_head_provenance=_provenance(),
        sealed_chain=_chain(),
    )


def test_production_equivalence_certificate_exact_round_trip() -> None:
    value = _certificate()
    assert (
        validate_production_equivalence_certificate(
            value, implementation_head=HEAD, manifest_sha256=SHA
        )
        == value
    )


@pytest.mark.parametrize(
    "mutation",
    (
        "missing_role",
        "extra_role",
        "wrong_root",
        "wrong_count",
        "fresh_used",
        "mutation_coverage",
        "evaluation_head",
        "evaluation_manifest",
    ),
)
def test_production_equivalence_certificate_mutations_fail(
    mutation: str,
) -> None:
    value = copy.deepcopy(_certificate())
    if mutation == "missing_role":
        del value["sealed_chain"]["execution_review"]
    elif mutation == "extra_role":
        value["sealed_chain"]["other"] = value["sealed_chain"]["authority"]
    elif mutation == "wrong_root":
        value["sealed_chain"]["execution"]["root_sha256"] = "x" * 64
    elif mutation == "wrong_count":
        value["tick_count"] = 575
    elif mutation == "fresh_used":
        value["fresh_rows_or_outcomes_used"] = True
    elif mutation == "mutation_coverage":
        value["mutation_coverage"].pop()
    elif mutation == "evaluation_head":
        value["dual_head_provenance"][
            "evaluation_implementation_head"
        ] = "d" * 40
    else:
        value["dual_head_provenance"][
            "evaluation_critical_implementation_manifest_sha256"
        ] = "d" * 64
    payload = copy.deepcopy(value)
    payload.pop("certificate_payload_sha256")
    value["certificate_payload_sha256"] = canonical_sha256(payload)
    with pytest.raises(ValueError):
        validate_production_equivalence_certificate(
            value, implementation_head=HEAD, manifest_sha256=SHA
        )


def test_production_equivalence_freeze_rejects_cross_role_root_swap() -> None:
    provenance = _provenance()
    provenance["execution_root_sha256"] = _chain()["execution_review"][
        "root_sha256"
    ]
    with pytest.raises(ValueError, match="dual-HEAD binding"):
        freeze_production_equivalence_certificate(
            implementation_head=HEAD,
            manifest_sha256=SHA,
            holdout_identity_sha256="3" * 64,
            experiment_protocol_sha256="4" * 64,
            dual_head_provenance=provenance,
            sealed_chain=_chain(),
        )


def test_independent_reviewers_reject_dual_head_provenance_mutations(
) -> None:
    reviewer = independent_validate_evaluation_dual_head_provenance
    assert reviewer(_provenance()) == _provenance()
    for field, invalid in (
        ("execution_implementation_head", "e" * 39),
        ("execution_critical_implementation_manifest_sha256", "x" * 64),
        ("opening_release_root_sha256", True),
        ("scientific_exposure_ledger_sha256", "0" * 63),
        ("execution_root_sha256", "9" * 40),
        ("execution_review_root_sha256", None),
        ("evaluation_implementation_head", "1" * 64),
        ("evaluation_critical_implementation_manifest_sha256", "2" * 40),
    ):
        value = copy.deepcopy(_provenance())
        value[field] = invalid
        with pytest.raises(ValueError, match="dual-HEAD"):
            reviewer(value)


def test_independent_reviewer_rejects_all_cross_role_value_swaps() -> None:
    provenance = _provenance()
    release = {
        "implementation_source_head": provenance[
            "execution_implementation_head"
        ],
        "critical_implementation_manifest_sha256": provenance[
            "execution_critical_implementation_manifest_sha256"
        ],
    }
    execution_report = {
        "opening_consumption": {
            "scientific_ledger_sha256": provenance[
                "scientific_exposure_ledger_sha256"
            ]
        }
    }
    roots = {
        name: provenance[field]
        for name, field in (
            ("opening_release", "opening_release_root_sha256"),
            ("execution", "execution_root_sha256"),
            ("execution_review", "execution_review_root_sha256"),
        )
    }
    kwargs = {
        "opening_release": release,
        "execution_artifact_report": execution_report,
        "sealed_chain_roots": roots,
        "evaluation_implementation_head": provenance[
            "evaluation_implementation_head"
        ],
        "evaluation_critical_implementation_manifest_sha256": provenance[
            "evaluation_critical_implementation_manifest_sha256"
        ],
    }
    assert (
        independent_validate_evaluation_role_bindings(
            provenance, **kwargs
        )
        == provenance
    )
    for field in (
        "execution_implementation_head",
        "execution_critical_implementation_manifest_sha256",
        "opening_release_root_sha256",
        "scientific_exposure_ledger_sha256",
        "execution_root_sha256",
        "execution_review_root_sha256",
        "evaluation_implementation_head",
        "evaluation_critical_implementation_manifest_sha256",
    ):
        mutated = copy.deepcopy(provenance)
        mutated[field] = (
            "d" * 40 if field.endswith("_head") else "d" * 64
        )
        with pytest.raises(ValueError, match="role binding"):
            independent_validate_evaluation_role_bindings(
                mutated, **kwargs
            )
