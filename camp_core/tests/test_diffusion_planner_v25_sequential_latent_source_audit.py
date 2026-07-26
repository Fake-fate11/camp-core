from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations import (
    diffusion_planner_v25_sequential_latent_source_audit as producer,
)
from camp_core.integrations import (
    diffusion_planner_v25_sequential_latent_source_audit_review as reviewer,
)


ROOT = Path(__file__).resolve().parents[2]


def _sources() -> dict[str, str]:
    diagnostic = (
        ROOT
        / "scripts"
        / "integrations"
        / "materialize_diffusion_planner_v25_fair_pool_calibration_first_state_diagnostic.py"
    ).read_text(encoding="utf-8")
    manifest = (
        ROOT
        / "camp_core"
        / "camp_core"
        / "integrations"
        / "diffusion_planner_v25_fair_pool_input_manifest_v2.py"
    ).read_text(encoding="utf-8")
    model = """
class Diffusion_Planner:
    def forward(self, inputs):
        encoder_outputs = self.encoder(inputs)
        decoder_outputs = self.decoder(encoder_outputs, inputs)
        return encoder_outputs, decoder_outputs
"""
    decoder = '''
class Decoder:
    def _inference_flow_matching(self, sampled_trajectories):
        x = sampled_trajectories
        x = euler_integration(func, x, NUM_STEP)
        return x
    def _inference_x_start(self, sampled_trajectories):
        xT = sampled_trajectories
        x0 = dpm_solver.sample(xT, steps=10, prefix_mask=mask, skip_type="logSNR")
        return x0
    def _forward_inference(self, inputs):
        sampled_trajectories = inputs["sampled_trajectories"].reshape(
            1, 321, 81 * 4
        )
        return self._inference_x_start(sampled_trajectories)
    def forward(self, encoding, inputs):
        return self._forward_inference(inputs)
'''
    return {
        "camp_diagnostic_materializer": diagnostic,
        "camp_input_manifest_v2": manifest,
        "fixed_dp_model": model,
        "fixed_dp_decoder": decoder,
    }


def _contract() -> dict:
    sources = _sources()
    return producer.source_audit_contract(
        implementation_head="1" * 40,
        exact_dirs={
            key: f"/tmp/{key}" for key in producer.EXACT_DIR_KEYS
        },
        source_sha256={
            key: hashlib.sha256(value.encode("utf-8")).hexdigest()
            for key, value in sources.items()
        },
        producer_source_sha256="2" * 64,
        reviewer_source_sha256="3" * 64,
    )


def test_authority_is_exact_canonical_and_zero_call() -> None:
    assert (
        hashlib.sha256(producer.HIGH_AUTHORITY_JSON.encode("ascii")).hexdigest()
        == producer.HIGH_AUTHORITY_SHA256
    )
    contract = _contract()
    producer.validate_source_audit_contract(contract)
    assert contract["new_model_pool_selector_call_count"] == 0
    assert contract["calibration_640_authorized"] is False
    assert contract["taxonomy"] == list(producer.TAXONOMY)
    reviewed = reviewer.review_source_audit_contract(
        contract,
        expected_implementation_head="1" * 40,
        expected_exact_dirs={
            key: f"/tmp/{key}" for key in producer.EXACT_DIR_KEYS
        },
        expected_source_sha256=contract["source_sha256"],
    )
    assert reviewed["status"] == "passed_independent_literal_contract_review"


def test_requested_latent_rebuild_exposes_broadcast_duplicate_rows() -> None:
    latent, raw, summary = producer.reconstruct_requested_latent()
    assert latent.shape == (8, 321, 81, 4)
    assert latent.dtype.str == "<f4"
    assert summary["tensor_sha256"] == (
        "b995f83f083df0321b8a575e10065aac041c14c30830129963048b73b7ebfea0"
    )
    assert summary["finite"] is True
    assert summary["unique_cardinality"] == 2
    assert summary["duplicate_groups"] == [[1, 2, 3, 4, 5, 6, 7]]
    assert len(raw) == int(np.prod(latent.shape)) * 4
    assert all(np.array_equal(latent[1], latent[index]) for index in range(2, 8))
    assert not np.array_equal(latent[0], latent[1])


def test_independent_reviewer_latent_literal_matches_producer_bytes() -> None:
    _latent, raw, summary = producer.reconstruct_requested_latent()
    review_raw, review_summary = reviewer._latent()
    assert review_raw == raw
    assert review_summary == summary


def test_static_source_dataflow_has_exact_ast_spans_and_bindings() -> None:
    result = producer.source_semantics(_sources())
    assert set(result) == {*producer.SOURCE_KEYS, "dataflow"}
    assert result["camp_diagnostic_materializer"]["function_spans"]["_latent"]
    assert result["fixed_dp_model"]["function_spans"]["forward"]
    assert "broadcast" in result["dataflow"][
        "clone_broadcast_index_seed_overwrite_default_ignored_argument"
    ]
    assert "xT" in result["dataflow"]["decoder_consumption"]


@pytest.mark.parametrize(
    ("source_key", "old", "new"),
    [
        (
            "camp_diagnostic_materializer",
            "standard_normal(value.shape[1:])",
            "standard_normal(value[1:].shape)",
        ),
        (
            "camp_diagnostic_materializer",
            'expanded["sampled_trajectories"] = latent_tensor.contiguous()',
            'expanded["sampled_trajectories"] = expanded["sampled_trajectories"]',
        ),
        (
            "camp_diagnostic_materializer",
            "value[row_index : row_index + 1].contiguous()",
            "value[0:1].contiguous()",
        ),
        (
            "camp_input_manifest_v2",
            "standard_normal(LATENT_SHAPE[1:])",
            "standard_normal((7, *LATENT_SHAPE[1:]))",
        ),
        (
            "fixed_dp_model",
            "self.decoder(encoder_outputs, inputs)",
            "self.decoder(encoder_outputs, {})",
        ),
        (
            "fixed_dp_decoder",
            "xT = sampled_trajectories",
            "xT = default_latent",
        ),
    ],
)
def test_static_dataflow_mutations_fail_closed(
    source_key: str, old: str, new: str
) -> None:
    sources = _sources()
    assert old in sources[source_key]
    sources[source_key] = sources[source_key].replace(old, new, 1)
    with pytest.raises(ValueError):
        producer.source_semantics(sources)


def test_contract_source_sha_and_taxonomy_mutations_fail_closed() -> None:
    contract = _contract()
    contract["required_source_tokens_sha256"]["fixed_dp_decoder"] = "4" * 64
    with pytest.raises(ValueError):
        producer.validate_source_audit_contract(contract)
    contract = _contract()
    contract["taxonomy"] = contract["taxonomy"][:-1]
    with pytest.raises(ValueError):
        producer.validate_source_audit_contract(contract)
    with pytest.raises(ValueError):
        reviewer.review_source_audit_contract(
            contract,
            expected_implementation_head="1" * 40,
            expected_exact_dirs={
                key: f"/tmp/{key}" for key in producer.EXACT_DIR_KEYS
            },
            expected_source_sha256=contract["source_sha256"],
        )


def test_missing_or_resealed_receipt_cannot_enter_producer() -> None:
    contract = _contract()
    with pytest.raises((KeyError, ValueError)):
        producer.materialize_source_audit(
            contract=contract,
            precondition_receipt={},
            first_state_manifest={},
            candidate_bytes=b"",
            neighbor_bytes=b"",
            source_texts=_sources(),
        )


def test_reviewer_rejects_arbitrary_authority_or_unsealed_receipt() -> None:
    contract = _contract()
    contract["high_authority_sha256"] = "5" * 64
    with pytest.raises(ValueError):
        reviewer.review_source_audit(
            contract=contract,
            audit_report={},
            requested_latent_bytes=b"",
            candidate_bytes=b"",
            neighbor_bytes=b"",
            precondition_receipt={},
            first_state_manifest={},
            source_texts=_sources(),
        )
    contract = _contract()
    with pytest.raises((KeyError, ValueError)):
        reviewer.review_source_audit(
            contract=contract,
            audit_report={},
            requested_latent_bytes=producer.reconstruct_requested_latent()[1],
            candidate_bytes=b"",
            neighbor_bytes=b"",
            precondition_receipt={},
            first_state_manifest={},
            source_texts=_sources(),
        )


def test_row_call_forward_output_permutations_change_binding_hash() -> None:
    bindings = {
        "input_manifest_sha256": "1" * 64,
        "actual_input_tensor_bundle_sha256": "2" * 64,
        "actual_state_sha256": "3" * 64,
        "latent_tensor_sha256": "4" * 64,
        "model_source_sha256": "5" * 64,
        "checkpoint_sha256": "6" * 64,
        "fixed_dp_head": "7" * 40,
    }
    base = producer._forward_id(
        index=0,
        bindings=bindings,
        candidate_row_sha256="8" * 64,
        neighbor_row_sha256="9" * 64,
    )
    assert base != producer._forward_id(
        index=1,
        bindings=bindings,
        candidate_row_sha256="8" * 64,
        neighbor_row_sha256="9" * 64,
    )
    assert base != producer._forward_id(
        index=0,
        bindings=bindings,
        candidate_row_sha256="a" * 64,
        neighbor_row_sha256="9" * 64,
    )
    assert base != producer._forward_id(
        index=0,
        bindings=bindings,
        candidate_row_sha256="8" * 64,
        neighbor_row_sha256="b" * 64,
    )
