from __future__ import annotations

import copy
from pathlib import Path
import re

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_industrial_bounded_closed_loop import (
    ARMS,
    AUTHORITY_SHA256,
    PARAMETER_NAMES,
    contract,
    latent_manifest,
    scalar_leaf_ids,
    tick_latent,
    validate_contract,
    validate_latency_row,
    validate_terminal_accounting,
)
from camp_core.integrations.diffusion_planner_v25_industrial_bounded_closed_loop_review import (
    review_contract_literal,
    review_evaluation,
    review_latent_manifest,
)
from camp_core.integrations.diffusion_planner_v25_industrial_evaluation_contract_v3 import (
    evaluation_contract_v3,
)


def test_contract_freezes_target_architecture_and_single_cluster_boundary() -> None:
    value = contract()
    assert value["authority_sha256"] == AUTHORITY_SHA256
    assert value["architecture"]["arms"] == list(ARMS)
    assert value["architecture"]["formal_model_calls_per_tick"] == 1
    assert value["architecture"]["sequential_model_calls"] == 0
    assert value["denominator"]["planned_ticks"] == 192
    assert value["evaluation"]["scalar_leaf_count"] == 161
    assert value["evaluation"]["inferential_status"] == (
        "not_evaluable_bounded_single_cluster"
    )
    assert value["evaluation"]["weighted_total_allowed"] is False
    assert value["evaluation"]["claim_authorized"] is False


def test_independent_reviewer_rebuilds_semantics() -> None:
    value = contract()
    reviewed = review_contract_literal(value, evaluation_contract_v3())
    assert reviewed == value
    for mutation in (
        ("architecture", "formal_model_calls_per_tick", 8),
        ("architecture", "sequential_model_calls", 1),
        ("denominator", "planned_ticks", 191),
        ("evaluation", "weighted_total_allowed", True),
        ("evaluation", "claim_authorized", True),
    ):
        bad = copy.deepcopy(value)
        bad[mutation[0]][mutation[1]] = mutation[2]
        with pytest.raises(ValueError):
            review_contract_literal(bad, evaluation_contract_v3())


def test_parameter_matrix_exact_and_no_implicit_defaults() -> None:
    value = contract()
    rows = value["pre_execution_hardening"]["parameter_propagation_matrix"]
    assert [row["parameter"] for row in rows] == list(PARAMETER_NAMES)
    assert all("no fallback" in row["producer_validation"] for row in rows)
    bad = copy.deepcopy(value)
    bad["pre_execution_hardening"]["parameter_propagation_matrix"][0][
        "frozen_value_or_rule"
    ] = "bare python"
    with pytest.raises(ValueError):
        validate_contract(bad)


def test_latent_manifest_is_same_tick_unique_k8_and_reviewer_rebuilds() -> None:
    rows = latent_manifest()
    assert len(rows) == 64
    assert len({row["tensor_sha256"] for row in rows}) == 64
    assert all(row["row_unique_cardinality"] == 8 for row in rows)
    assert all(row["row0_all_zero"] is True for row in rows)
    review_latent_manifest(rows)
    assert np.all(tick_latent(0)[0] == 0.0)
    bad = copy.deepcopy(rows)
    bad[7]["tensor_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        review_latent_manifest(bad)


def test_terminal_denominator_retains_failures_and_unattempted() -> None:
    arms = [
        {
            "arm": arm,
            "complete_tick_count": 60,
            "failed_tick_count": 1,
            "unattempted_tick_count": 3,
        }
        for arm in ARMS
    ]
    assert validate_terminal_accounting(arms)["planned_ticks"] == 192
    bad = copy.deepcopy(arms)
    bad[0]["unattempted_tick_count"] = 2
    with pytest.raises(ValueError):
        validate_terminal_accounting(bad)


def test_baseline_latency_n_a_is_not_zero() -> None:
    baseline = {
        "pool_generation": 1.0,
        "atoms": None,
        "context": None,
        "weights": None,
        "selector_pure_incremental": None,
        "end_to_end": 2.0,
    }
    assert validate_latency_row("pool_matched_candidate0", baseline) == baseline
    bad = dict(baseline)
    bad["selector_pure_incremental"] = 0.0
    with pytest.raises(ValueError):
        validate_latency_row("pool_matched_candidate0", bad)


def test_industrial_leaf_topology_is_exact_161() -> None:
    ids = scalar_leaf_ids()
    assert len(ids) == 161
    assert len(set(ids)) == 161
    assert not any("SafetyCost" in value for value in ids)


def test_bounded_evaluation_rejects_missing_leaf_and_claim_mutations() -> None:
    industrial = evaluation_contract_v3()
    leaves = [
        {
            "leaf_id": row["leaf_id"],
            "status": "evidence_missing",
            "inferential_status": "not_evaluable_bounded_single_cluster",
        }
        for row in industrial["scalar_leaf_registry"]
    ]
    report = {
        "schema_version": "camp_dp_v25_industrial_v3_bounded_evaluation_v1",
        "inferential_status": "not_evaluable_bounded_single_cluster",
        "claim_authorized": False,
        "weighted_total_present": False,
        "legacy_safetycost_computed": False,
        "scalar_leaf_vector": leaves,
    }
    review_evaluation(report, [row["leaf_id"] for row in leaves])
    bad = copy.deepcopy(report)
    bad["scalar_leaf_vector"].pop()
    with pytest.raises(ValueError):
        review_evaluation(bad, [row["leaf_id"] for row in leaves])
    bad = copy.deepcopy(report)
    bad["claim_authorized"] = True
    with pytest.raises(ValueError):
        review_evaluation(bad, [row["leaf_id"] for row in leaves])


def test_target_entrypoint_has_explicit_latent_and_failure_keywords() -> None:
    source = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "integrations"
        / "run_diffusion_planner_v25_industrial_bounded_closed_loop.py"
    ).read_text("utf-8")
    for literal in (
        "latent_provider=tick_latent",
        "post_safety_enricher=_post_safety_enricher",
        "retain_runtime_failures=True",
        "evaluate_all_arms=False",
        "adaptation_diagnostics=False",
    ):
        assert literal in source


def test_new_v25_wrappers_reject_bare_python_invocation() -> None:
    root = Path(__file__).resolve().parents[2]
    files = (
        root / "scripts" / "integrations" / "freeze_diffusion_planner_v25_industrial_bounded_closed_loop.py",
        root / "scripts" / "integrations" / "review_diffusion_planner_v25_industrial_bounded_closed_loop.py",
        root / "scripts" / "integrations" / "run_diffusion_planner_v25_industrial_bounded_closed_loop.py",
    )
    pattern = re.compile(r"(^|[;&| ])python(?:3)?(?:[ .]|$)", re.MULTILINE)
    assert all(pattern.search(path.read_text("utf-8")) is None for path in files)
