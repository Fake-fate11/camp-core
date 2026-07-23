from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_v25_production_equivalence_certificate import (
    freeze_production_equivalence_certificate,
    validate_production_equivalence_certificate,
)


HEAD = "1" * 40
SHA = "2" * 64
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


def _certificate() -> dict:
    return freeze_production_equivalence_certificate(
        implementation_head=HEAD,
        manifest_sha256=SHA,
        holdout_identity_sha256="3" * 64,
        experiment_protocol_sha256="4" * 64,
        sealed_chain={
            role: {
                "path": f"/root/autodl-tmp/nonfresh_{role}",
                "root_sha256": f"{index + 5:x}" * 64,
            }
            for index, role in enumerate(ROLES)
        },
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
    else:
        value["mutation_coverage"].pop()
    with pytest.raises(ValueError):
        validate_production_equivalence_certificate(
            value, implementation_head=HEAD, manifest_sha256=SHA
        )
