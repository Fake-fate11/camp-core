from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_v25_role_provenance import (
    freeze_evaluation_dual_head_provenance,
    validate_evaluation_dual_head_provenance,
)
from camp_core.integrations.diffusion_planner_v25_role_provenance_review import (
    independent_validate_evaluation_dual_head_provenance,
)


def _provenance() -> dict[str, str]:
    return freeze_evaluation_dual_head_provenance(
        execution_implementation_head="1" * 40,
        execution_critical_implementation_manifest_sha256="2" * 64,
        opening_release_root_sha256="3" * 64,
        scientific_exposure_ledger_sha256="4" * 64,
        execution_root_sha256="5" * 64,
        execution_review_root_sha256="6" * 64,
        evaluation_implementation_head="7" * 40,
        evaluation_critical_implementation_manifest_sha256="8" * 64,
    )


def test_evaluation_dual_head_provenance_exact_round_trip() -> None:
    value = _provenance()
    assert validate_evaluation_dual_head_provenance(value) == value
    assert independent_validate_evaluation_dual_head_provenance(value) == value


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("execution_implementation_head", "1" * 39),
        ("execution_critical_implementation_manifest_sha256", "x" * 64),
        ("opening_release_root_sha256", "3" * 63),
        ("scientific_exposure_ledger_sha256", "4" * 65),
        ("execution_root_sha256", None),
        ("execution_review_root_sha256", True),
        ("evaluation_implementation_head", "7" * 64),
        ("evaluation_critical_implementation_manifest_sha256", "8" * 40),
    ),
)
def test_evaluation_dual_head_provenance_mutations_fail(
    field: str, value: object
) -> None:
    mutated = copy.deepcopy(_provenance())
    mutated[field] = value
    with pytest.raises(ValueError, match="dual-HEAD"):
        validate_evaluation_dual_head_provenance(mutated)
    with pytest.raises(ValueError, match="dual-HEAD"):
        independent_validate_evaluation_dual_head_provenance(mutated)


def test_evaluation_dual_head_provenance_missing_and_extra_fail() -> None:
    missing = copy.deepcopy(_provenance())
    del missing["scientific_exposure_ledger_sha256"]
    with pytest.raises(ValueError, match="field set"):
        validate_evaluation_dual_head_provenance(missing)
    with pytest.raises(ValueError, match="field set"):
        independent_validate_evaluation_dual_head_provenance(missing)
    extra = copy.deepcopy(_provenance())
    extra["futureOutcome"] = "forbidden"
    with pytest.raises(ValueError, match="field set"):
        validate_evaluation_dual_head_provenance(extra)
    with pytest.raises(ValueError, match="field set"):
        independent_validate_evaluation_dual_head_provenance(extra)
