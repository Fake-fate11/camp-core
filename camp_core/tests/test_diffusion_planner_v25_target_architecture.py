from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v25_target_architecture import (
    CAPABILITY_SCHEMA,
    FIXED_DP_HEAD,
    LEGACY_DECISION,
    array_sha256,
    canonical_sha256,
    freeze_candidate_pool,
    qualify_selector_after_pool,
    target_architecture_amendment,
    validate_capability_report,
    validate_target_architecture_amendment,
)
from camp_core.integrations.diffusion_planner_v25_target_architecture_review import (
    independently_review_amendment,
    independently_review_capability,
)


ROOT = Path(__file__).resolve().parents[2]


def _pool() -> tuple[np.ndarray, object]:
    tensor = np.arange(8 * 5 * 4, dtype=np.float32).reshape(8, 5, 4)
    pool = freeze_candidate_pool(
        tensor,
        input_sha256="1" * 64,
        model_sha256="2" * 64,
        forward_invocation_id="forward-1",
    )
    return tensor, pool


def _capability_report() -> dict:
    tensor, pool = _pool()
    arms = [
        qualify_selector_after_pool(
            pool,
            arm=arm,
            selector=lambda _pool, _guard: 0,
        )
        for arm in ("pool_baseline", "Static14D", "Scene14D")
    ]
    rng = "a" * 64
    return {
        "schema_version": CAPABILITY_SCHEMA,
        "status": "passed_same_ego_single_invocation_k8_capability",
        "authority": {
            "contract_path": "/tmp/contract",
            "contract_root_sha256": "3" * 64,
            "contract_review_path": "/tmp/review",
            "contract_review_root_sha256": "4" * 64,
        },
        "fixed_dp": {
            "head": FIXED_DP_HEAD,
            "repo": "/tmp/Diffusion-Planner",
            "checkpoint_path": "/tmp/model.pth",
            "checkpoint_sha256": "2" * 64,
            "args_path": "/tmp/args.json",
            "args_sha256": "5" * 64,
            "model_source_sha256": "6" * 64,
            "decoder_source_sha256": "7" * 64,
            "encoder_source_sha256": "8" * 64,
            "source_modified": False,
            "checkpoint_modified": False,
            "model_eval_mode": True,
            "formal_entrypoint": "Diffusion_Planner.forward(inputs)",
        },
        "source_state": {
            "role": "development_nonholdout",
            "route_role": "v24_source_only_single_record_probe",
            "route_sha256": "9" * 64,
            "source_batch_size": 1,
            "state_sha256": "b" * 64,
            "input_sha256": "1" * 64,
            "simulator_steps_advanced": 0,
            "holdout_or_fresh_accessed": False,
        },
        "candidate_axis": {
            "semantics": "same_ego_candidate_batch",
            "candidate_count": 8,
            "source_agent_ids": ["ego"],
            "source_batch_size": 1,
            "expanded_model_batch_size": 8,
            "agent_as_ego_batch": False,
            "all_nonlatent_rows_identical": True,
        },
        "latent": {
            "source": "legacy_candidate_latents_seed24001_noise_scale1",
            "seed": 24001,
            "noise_scale": 1.0,
            "shape": [8, 321, 81, 4],
            "dtype": "float32",
            "sha256": "c" * 64,
            "row_sha256": [f"{index:x}".zfill(64) for index in range(8)],
            "row0_zero": True,
            "finite": True,
        },
        "temperature": {
            "status": "not_exposed_by_fixed_dp_formal_interface",
            "tensor": None,
            "sha256": None,
        },
        "primary_pool_invocation": {
            "forward_invocation_id": "forward-1",
            "model_call_count": 1,
            "input_sha256": "1" * 64,
            "input_batch_size": 8,
            "output_shape": [8, 5, 4],
            "dtype": "float32",
            "finite": True,
            "candidate_tensor_sha256": array_sha256(tensor),
            "row_sha256": [array_sha256(row) for row in tensor],
            "unique_row_sha256_count": 8,
            "pool_id": pool.pool_id,
            "pairwise_rms_min": 1.0,
            "pairwise_rms_max": 2.0,
            "diverse": True,
        },
        "determinism": {
            "repeat_model_call_count": 1,
            "repeat_tensor_sha256": array_sha256(tensor),
            "exact_equal": True,
            "max_abs_error": 0.0,
        },
        "batch_vs_sequential": {
            "relationship": (
                "same_state_same_latent_direct_batch8_vs_eight_batch1_calls"
            ),
            "sequential_model_call_count": 8,
            "atol": 1e-5,
            "rtol": 1e-5,
            "within_frozen_tolerance": True,
            "per_row_max_abs_error": [0.0] * 8,
            "max_abs_error": 0.0,
            "all_sequential_row_sha256": [
                array_sha256(row) for row in tensor
            ],
            "distribution_equivalent_under_frozen_row_tolerance": True,
        },
        "selector_after_pool": {
            "status": "passed_three_arm_structural_pool_binding_gate",
            "selection_semantics": (
                "outcome_independent_row0_structural_probe_not_camp_score_evaluation"
            ),
            "arms": arms,
            "all_arms_same_pool": True,
            "selector_model_call_count_total": 0,
        },
        "rng_boundary": {
            "unchanged": True,
            "before_sha256": rng,
            "after_sha256": rng,
        },
        "training_decision": {
            "training_executed": False,
            "batch_vs_sequential_equivalent": True,
            "possible_ood_effect_requires_future_adjudication": False,
        },
        "claim_boundary": {
            "fresh_or_closed_loop_executed": False,
            "scientific_effect_claim_authorized": False,
            "legacy_claim_decision": LEGACY_DECISION,
            "qualification_only": True,
        },
    }


def test_amendment_is_literal_outcome_independent_and_independently_reviewable() -> None:
    amendment = target_architecture_amendment()
    assert validate_target_architecture_amendment(amendment) == amendment
    assert independently_review_amendment(amendment) == amendment
    assert (
        amendment["superseding_additive_classification"][
            "existing_b4_architecture_class"
        ]
        == "compute_augmented_candidate_expansion_plus_reranking"
    )
    assert amendment["claim_boundary"]["fresh_authorized"] is False


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("outcome_independent",), False),
        (
            ("superseding_additive_classification", "operational_default_batch_size"),
            8,
        ),
        (
            ("superseding_additive_classification", "selector_model_call_count_required"),
            1,
        ),
        (("claim_boundary", "new_scientific_effect_claim_authorized"), True),
    ],
)
def test_amendment_drift_fails_closed(path: tuple[str, ...], value: object) -> None:
    amendment = target_architecture_amendment()
    cursor = amendment
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    with pytest.raises(ValueError):
        validate_target_architecture_amendment(amendment)
    with pytest.raises(ValueError):
        independently_review_amendment(amendment)


def test_amendment_unknown_field_fails_closed() -> None:
    amendment = target_architecture_amendment()
    amendment["unknown"] = True
    with pytest.raises(ValueError):
        validate_target_architecture_amendment(amendment)
    with pytest.raises(ValueError):
        independently_review_amendment(amendment)


def test_freeze_pool_binds_tensor_input_model_and_forward() -> None:
    tensor, pool = _pool()
    expected = canonical_sha256(
        {
            "tensor_sha256": array_sha256(tensor),
            "input_sha256": "1" * 64,
            "model_sha256": "2" * 64,
            "forward_invocation_id": "forward-1",
        }
    )
    assert pool.pool_id == expected
    assert pool.tensor_sha256 == array_sha256(tensor)
    assert pool.tensor.flags.writeable is False


@pytest.mark.parametrize("shape", [(7, 5, 4), (8, 5), (8, 5, 1)])
def test_freeze_pool_rejects_wrong_shape(shape: tuple[int, ...]) -> None:
    with pytest.raises(ValueError, match="candidate pool"):
        freeze_candidate_pool(
            np.zeros(shape, dtype=np.float32),
            input_sha256="1" * 64,
            model_sha256="2" * 64,
            forward_invocation_id="f",
        )


def test_three_arms_bind_same_pool_and_zero_generation_calls() -> None:
    _tensor, pool = _pool()
    receipts = [
        qualify_selector_after_pool(
            pool, arm=arm, selector=lambda _pool, _guard: 0
        )
        for arm in ("pool_baseline", "Static14D", "Scene14D")
    ]
    assert len({row["pool_id"] for row in receipts}) == 1
    assert len({row["candidate_tensor_sha256"] for row in receipts}) == 1
    assert {row["model_call_count_after_pool"] for row in receipts} == {0}


def test_pool_baseline_is_frozen_row0() -> None:
    _tensor, pool = _pool()
    with pytest.raises(ValueError, match="row0"):
        qualify_selector_after_pool(
            pool,
            arm="pool_baseline",
            selector=lambda _pool, _guard: 1,
        )


@pytest.mark.parametrize(
    "forbidden",
    ["model_callback", "replace_latent", "generate_trajectory"],
)
def test_selector_forbidden_operations_fail_closed(forbidden: str) -> None:
    _tensor, pool = _pool()

    def selector(_pool, guard):
        getattr(guard, forbidden)()
        return 0

    with pytest.raises(RuntimeError, match="forbidden"):
        qualify_selector_after_pool(pool, arm="Static14D", selector=selector)


def test_synthetic_single_invocation_same_ego_batch_produces_k8() -> None:
    class Model:
        def __init__(self) -> None:
            self.calls = 0

        def __call__(self, state: np.ndarray, latent: np.ndarray) -> np.ndarray:
            self.calls += 1
            return state[:, None, :] + latent

    model = Model()
    source_state = np.array([[1.0, 2.0]], dtype=np.float32)
    latent = np.arange(8 * 3 * 2, dtype=np.float32).reshape(8, 3, 2)
    expanded = np.repeat(source_state, 8, axis=0)
    candidates = model(expanded, latent)
    assert model.calls == 1
    assert candidates.shape == (8, 3, 2)
    assert np.array_equal(expanded, np.repeat(expanded[:1], 8, axis=0))


def test_qualifier_clones_mutable_model_inputs_and_seals_latent_preimage() -> None:
    source = (
        ROOT / "scripts/integrations/qualify_diffusion_planner_v25_same_ego_k8.py"
    ).read_text(encoding="utf-8")
    assert "latent_preimage_np = latent_preimage.detach().cpu().numpy().copy()" in source
    assert "call_inputs = {" in source
    assert "value.detach().clone() for key, value in inputs.items()" in source
    assert "_encoded, outputs = model(call_inputs)" in source


def test_agent_as_ego_axis_is_rejected_by_capability_oracles() -> None:
    report = _capability_report()
    report["candidate_axis"]["agent_as_ego_batch"] = True
    report["candidate_axis"]["source_agent_ids"] = [f"agent-{i}" for i in range(8)]
    with pytest.raises(ValueError, match="axis"):
        validate_capability_report(report)
    with pytest.raises(ValueError, match="axis"):
        independently_review_capability(report)


def test_capability_report_passes_both_oracles() -> None:
    report = _capability_report()
    assert validate_capability_report(report) == report
    assert independently_review_capability(report) == report


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("primary_pool_invocation", "model_call_count", 2),
        ("determinism", "exact_equal", False),
        ("batch_vs_sequential", "sequential_model_call_count", 7),
        ("batch_vs_sequential", "within_frozen_tolerance", False),
        ("rng_boundary", "unchanged", False),
        ("claim_boundary", "scientific_effect_claim_authorized", True),
    ],
)
def test_capability_drift_fails_closed(
    section: str, field: str, value: object
) -> None:
    report = _capability_report()
    report[section][field] = value
    with pytest.raises(ValueError):
        validate_capability_report(report)
    with pytest.raises(ValueError):
        independently_review_capability(report)


def test_capability_unknown_field_fails_closed() -> None:
    report = _capability_report()
    report["unknown"] = True
    with pytest.raises(ValueError, match="fields"):
        validate_capability_report(report)
    with pytest.raises(ValueError, match="fields"):
        independently_review_capability(report)


def test_old_b4_hook_is_explicitly_sequential_candidate_expansion() -> None:
    source = (
        ROOT / "scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py"
    ).read_text(encoding="utf-8")
    assert "outputs = _model_outputs(model, batched)" in source
    assert "for index in range(1, 8):" in source
    assert "_model_outputs(model, candidate_data)" in source


def test_reviewer_does_not_import_producer_contract_module() -> None:
    source = (
        ROOT
        / "camp_core/camp_core/integrations/"
        "diffusion_planner_v25_target_architecture_review.py"
    ).read_text(encoding="utf-8")
    assert "diffusion_planner_v25_target_architecture import" not in source


def test_result_reviewer_checks_mutable_input_preimage_proof() -> None:
    source = (
        ROOT / "scripts/integrations/review_diffusion_planner_v25_same_ego_k8.py"
    ).read_text(encoding="utf-8")
    assert "_encoded, outputs = model(call_inputs)" in source
    assert "value.detach().clone() for key, value in inputs.items()" in source
    assert "latent_preimage_np = latent_preimage.detach().cpu().numpy().copy()" in source


def test_fairness_draft_separates_state_matched_and_compute_matched() -> None:
    draft = target_architecture_amendment()["fairness_contract_draft"]
    assert draft["state_matched_offline_selector_replay"]["same_k8_tensor"] is True
    assert (
        draft["compute_matched_closed_loop"][
            "post_divergence_cross_arm_tensor_identity_claimed"
        ]
        is False
    )
    assert (
        draft["latency_accounting"]["baseline_includes_pool_generation_cost"]
        is True
    )
    assert draft["statistics_endpoints_claim"]["authorized"] is False
