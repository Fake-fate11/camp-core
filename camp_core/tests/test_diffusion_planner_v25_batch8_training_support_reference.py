from __future__ import annotations

from copy import deepcopy
import hashlib
import inspect

import numpy as np
import pytest

from scripts.integrations import (
    materialize_diffusion_planner_v25_batch8_training_support_reference_preflight
    as preflight,
)
from camp_core.integrations import (
    diffusion_planner_v25_batch8_training_support_reference as reference,
)
from camp_core.integrations import (
    diffusion_planner_v25_batch8_training_support_reference_review as review,
)


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _git_sha(label: str) -> str:
    return _sha(label)[:40]


def _source_row(index: int) -> dict:
    family = reference.FAMILIES[index % len(reference.FAMILIES)]
    tier = reference.RISK_TIERS[(index // 7) % 3]
    source_class = reference.SOURCE_AVAILABILITY[(index // 21) % 2]
    geometry_mode = (index // 42) % 3
    if geometry_mode == 0:
        route = [[0.0, 0.0], [20.0, 0.0], [40.0, 0.0]]
    elif geometry_mode == 1:
        route = [[0.0, 0.0], [20.0, 0.0], [40.0, 10.0]]
    else:
        route = [[0.0, 0.0], [10.0, 0.0], [10.0, 20.0]]
    semantic = {
        "schema_version": "camp_dp_v25_semantic_clone_payload_v3",
        "family": family,
        "tier": tier,
        "route_polyline_local_m": route,
        "instance": index,
    }
    chain = {
        "semantic_clone_payload": semantic,
        "semantic_clone_sha256": reference.sha256_json(semantic),
        "route_geometry_sha256": _sha(f"geometry:{index}"),
        "source_chain_sha256": _sha(f"chain:{index}"),
    }
    return {
        "runner_eligible": True,
        "retention_role": "executable",
        "family": family,
        "tier": tier,
        "seed": 25001,
        "source_class": source_class,
        "source_map_sha256": _sha(f"map:{index // 4}"),
        "route_identity_sha256": _sha(f"route:{index}"),
        "formal_case_sha256": _sha(f"case:{index}"),
        "source_chain": chain,
    }


def _contract() -> dict:
    exact_dirs = {
        key: f"/root/autodl-tmp/training_support_{key}_deadbeef_1c3f6c17"
        for key in reference.EXACT_DIR_KEYS
    }
    source_sha = {
        "producer": _sha("producer"),
        "reviewer": _sha("reviewer"),
        "freeze": _sha("freeze"),
        "review_script": _sha("review-script"),
        "preflight": _sha("preflight"),
        "preflight_review": _sha("preflight-review"),
        "raw": _sha("raw"),
        "raw_review": _sha("raw-review"),
        "tests": _sha("tests"),
    }
    return reference.contract_payload(
        implementation_head=_git_sha("implementation"),
        pointer_head_at_authority=(
            "0df332d844a3dc3bec063c062e9e0ba8aebbbafc"
        ),
        exact_dirs=exact_dirs,
        source_sha256=source_sha,
    )


def test_authority_contract_and_independent_review() -> None:
    payload = _contract()
    assert reference.validate_contract(payload) == payload
    assert review.review_contract(payload) == payload
    assert (
        hashlib.sha256(reference.HIGH_AUTHORITY_JSON.encode("ascii")).hexdigest()
        == reference.HIGH_AUTHORITY_SHA256
    )


def test_input_only_capture_uses_the_frozen_training_step_count() -> None:
    source = inspect.getsource(preflight._capture_one)
    assert 'max_steps=int(config["protocol"]["corpus_steps"])' in source
    assert "max_steps=1" not in source


def test_zero_overlap_reads_the_sealed_fresh_b4_runtime_manifest() -> None:
    source = inspect.getsource(preflight._inventory_layers_from_b4)
    assert "fresh_b4_prepared_runtime_cases.json" in source
    assert 'B4_PREOPEN / "prepared_runtime_cases.json"' not in source


def test_unique_latent_is_row0_zero_and_eight_unique() -> None:
    latent = reference.materialize_latent(12345)
    manifest = reference.latent_manifest(12345)
    assert latent.shape == (8, 321, 81, 4)
    assert latent.dtype.str == "<f4"
    assert np.count_nonzero(latent[0]) == 0
    assert manifest["unique_row_sha256_count"] == 8
    assert manifest == reference.latent_manifest(12345)


def test_route_geometry_bins_are_frozen() -> None:
    assert (
        reference.route_geometry_bin([[0, 0], [10, 0], [20, 0]])
        == reference.ROUTE_GEOMETRY_BINS[0]
    )
    assert (
        reference.route_geometry_bin([[0, 0], [10, 0], [20, 5]])
        == reference.ROUTE_GEOMETRY_BINS[1]
    )
    assert (
        reference.route_geometry_bin([[0, 0], [10, 0], [10, 20]])
        == reference.ROUTE_GEOMETRY_BINS[2]
    )


def test_largest_remainder_requires_every_nonempty_cell() -> None:
    counts = {
        ("a", "b", "c", "d"): 700,
        ("e", "f", "g", "h"): 500,
    }
    quota = reference.largest_remainder_quotas(counts)
    assert quota == {
        ("a", "b", "c", "d"): 583,
        ("e", "f", "g", "h"): 417,
    }
    assert sum(quota.values()) == 1000
    with pytest.raises(ValueError):
        reference.largest_remainder_quotas(
            {(str(i), "x", "y", "z"): 1 for i in range(1001)}
        )


def test_manifest_selection_is_exact_no_replacement_and_reviewed() -> None:
    rows = [_source_row(index) for index in range(1500)]
    manifest = reference.select_manifest_entries(rows)
    assert manifest["selected_pool_count"] == 1000
    assert manifest["candidate_row_count"] == 8000
    assert len({row["clone_key_sha256"] for row in manifest["entries"]}) == 1000
    eligible = [
        reference.finalize_pool_manifest_entry(
            reference.build_clone_payload(row),
            actual_input_tensors={
                "source_only_selection_guard": np.asarray(
                    [[index]], dtype=np.int64
                )
            },
        )
        for index, row in enumerate(rows)
    ]
    result = review.review_selected_manifest(
        manifest,
        eligible_entries=eligible,
    )
    assert result["selected_pool_count"] == 1000
    assert result["family_count"] == 7


def test_duplicate_clone_and_capacity_below_1000_fail_before_model() -> None:
    rows = [_source_row(index) for index in range(1000)]
    rows[-1] = deepcopy(rows[0])
    with pytest.raises(ValueError, match="not unique"):
        reference.select_manifest_entries(rows)
    with pytest.raises(ValueError, match="below 1000"):
        reference.select_manifest_entries(
            [_source_row(index) for index in range(999)]
        )


def test_quantile_indices_and_intervals_are_inclusive() -> None:
    assert reference.inclusive_quantile_indices(8000) == {
        "q0_005_lower_index": 39,
        "q0_995_upper_index": 7960,
    }
    assert reference.inclusive_quantile_indices(1000) == {
        "q0_005_lower_index": 4,
        "q0_995_upper_index": 995,
    }
    values = list(range(1000))
    assert reference.inclusive_reference_interval(values) == review.reference(
        values
    )
    assert reference.inclusive_reference_interval(values)["q0_005_lower"] == 4
    assert reference.inclusive_reference_interval(values)["q0_995_upper"] == 995


def test_field_registry_has_16_row_and_4_pool_fields() -> None:
    row = reference.row_field_registry()
    pool = reference.pool_field_registry()
    assert len(row) == 16
    assert len(pool) == 4
    assert {item["field_id"] for item in row} == {
        *(f"normalized_atom_{index:02d}" for index in range(14)),
        "score_static14d",
        "score_scene14d",
    }
    assert all(item["independent_n"] == 1000 for item in row + pool)
    assert all(item["descriptive_value_count"] == 8000 for item in row)


def _receipt_topology_fixture() -> tuple[dict, list[dict]]:
    entries = []
    receipts = []
    for ordinal in range(1000):
        entry = {
            "pool_ordinal": ordinal,
            "pool_id": f"training_support:{ordinal:04d}",
            "actual_state_sha256": _sha(f"actual-state:{ordinal}"),
            "manifest_entry_sha256": _sha(f"entry:{ordinal}"),
        }
        entries.append(entry)
        receipts.append(
            {
                "pool_ordinal": ordinal,
                "pool_id": entry["pool_id"],
                "manifest_entry_sha256": entry["manifest_entry_sha256"],
                "formal_model_call_count": 1,
                "selector_receipt_count": 2,
                "post_pool_model_call_count": 0,
                "post_pool_dp_call_count": 0,
                "post_pool_latent_generation_count": 0,
                "post_pool_candidate_generation_count": 0,
                "outcome_fields_read": [],
                "status": "complete",
                "candidate_row_sha256": [
                    _sha(f"candidate:{ordinal}:{row}") for row in range(8)
                ],
            }
        )
    return {"selected_pool_count": 1000, "entries": entries}, receipts


def test_pool_receipt_topology_rejects_inflated_calls_ids_and_drops() -> None:
    manifest, receipts = _receipt_topology_fixture()
    assert reference.validate_pool_receipt_topology(manifest, receipts) == {
        "pool_slot_count": 1000,
        "complete_pool_count": 1000,
        "failed_pool_count": 0,
        "formal_model_call_count": 1000,
        "selector_receipt_count": 2000,
        "unique_actual_state_count": 1000,
    }
    for field, replacement in (
        ("pool_id", "forged-pool"),
        ("formal_model_call_count", 8),
        ("post_pool_model_call_count", 1),
    ):
        bad = deepcopy(receipts)
        bad[3][field] = replacement
        with pytest.raises(ValueError):
            reference.validate_pool_receipt_topology(manifest, bad)
    with pytest.raises(ValueError):
        reference.validate_pool_receipt_topology(manifest, receipts[:-1])


def test_pool_receipt_topology_rejects_duplicate_state_and_rows() -> None:
    manifest, receipts = _receipt_topology_fixture()
    bad_manifest = deepcopy(manifest)
    bad_manifest["entries"][1]["actual_state_sha256"] = bad_manifest["entries"][0][
        "actual_state_sha256"
    ]
    with pytest.raises(ValueError, match="duplicate"):
        reference.validate_pool_receipt_topology(bad_manifest, receipts)
    bad_receipts = deepcopy(receipts)
    bad_receipts[0]["candidate_row_sha256"][7] = bad_receipts[0][
        "candidate_row_sha256"
    ][6]
    with pytest.raises(ValueError, match="eight unique"):
        reference.validate_pool_receipt_topology(manifest, bad_receipts)


def test_actual_input_mutation_changes_state_and_clone_authority() -> None:
    base = reference.build_clone_payload(_source_row(0))
    first = reference.finalize_pool_manifest_entry(
        base,
        actual_input_tensors={"x": np.zeros((1, 3), dtype=np.float32)},
    )
    second = reference.finalize_pool_manifest_entry(
        base,
        actual_input_tensors={"x": np.ones((1, 3), dtype=np.float32)},
    )
    assert first["actual_state_sha256"] != second["actual_state_sha256"]
    assert first["clone_key_sha256"] != second["clone_key_sha256"]


def test_reference_cache_rejects_row_inflation_and_posthoc_quantile() -> None:
    row_values = {
        row["field_id"]: np.arange(8000, dtype=np.float64)
        for row in reference.row_field_registry()
    }
    pool_values = {
        row["field_id"]: np.arange(1000, dtype=np.float64)
        for row in reference.pool_field_registry()
    }
    row_refs = {
        key: reference.inclusive_reference_interval(value)
        for key, value in row_values.items()
    }
    pool_refs = {
        key: reference.inclusive_reference_interval(value)
        for key, value in pool_values.items()
    }
    assert reference.validate_reference_cache(
        row_values=row_values,
        pool_values=pool_values,
        row_references=row_refs,
        pool_references=pool_refs,
    )["row_value_count_per_field"] == 8000
    bad_values = deepcopy(row_values)
    bad_values["score_static14d"] = np.arange(8001, dtype=np.float64)
    with pytest.raises(ValueError, match="denominator"):
        reference.validate_reference_cache(
            row_values=bad_values,
            pool_values=pool_values,
            row_references=row_refs,
            pool_references=pool_refs,
        )
    bad_refs = deepcopy(row_refs)
    bad_refs["score_scene14d"]["q0_995_upper"] += 1.0
    with pytest.raises(ValueError, match="cache drifted"):
        reference.validate_reference_cache(
            row_values=row_values,
            pool_values=pool_values,
            row_references=bad_refs,
            pool_references=pool_refs,
        )


def test_zero_overlap_rejects_cross_split_clone() -> None:
    selected = [_sha(f"selected:{index}") for index in range(1000)]
    forbidden = {
        split: [_sha(f"{split}:{index}") for index in range(3)]
        for split in reference.ZERO_OVERLAP_SPLITS
    }
    assert reference.validate_zero_overlap(selected, forbidden)
    forbidden["Fresh_B4"][0] = selected[0]
    with pytest.raises(ValueError, match="overlaps Fresh_B4"):
        reference.validate_zero_overlap(selected, forbidden)


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("denominator", "pool_count"), 8000),
        (("denominator", "formal_model_invocations"), 8000),
        (("manifest_contract", "no_drop_no_replace"), False),
        (("pool_generation_contract", "formal_model_calls_per_pool"), 8),
        (("pool_generation_contract", "agent_as_ego_batch"), True),
        (("selector_contract", "same_immutable_candidate_tensor"), False),
        (
            (
                "selector_contract",
                "post_pool_model_dp_latent_candidate_generation_calls",
            ),
            1,
        ),
        (("support_field_contract", "weighted_total_created"), True),
        (("claim_authorized",), True),
        (("training_or_retraining_authorized",), True),
    ],
)
def test_contract_mutations_fail_both_oracles(
    path: tuple[str, ...], replacement: object
) -> None:
    payload = _contract()
    node = payload
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = replacement
    with pytest.raises(ValueError):
        reference.validate_contract(payload)
    with pytest.raises(ValueError):
        review.review_contract(payload)


def test_zero_overlap_requires_all_splits_and_empty_intersections() -> None:
    selected = [_sha(f"selected:{index}") for index in range(1000)]
    forbidden = {
        split: [_sha(f"{split}:{index}") for index in range(3)]
        for split in reference.ZERO_OVERLAP_SPLITS
    }
    assert reference.validate_zero_overlap(selected, forbidden) == {
        split: 3 for split in reference.ZERO_OVERLAP_SPLITS
    }
    forbidden["Fresh_B4"].append(selected[17])
    with pytest.raises(ValueError, match="Fresh_B4"):
        reference.validate_zero_overlap(selected, forbidden)


def test_manifest_mutation_and_row_inflation_fail_review() -> None:
    rows = [_source_row(index) for index in range(1500)]
    eligible = [reference.build_clone_payload(row) for row in rows]
    manifest = reference.select_manifest_entries(rows)
    forged = deepcopy(manifest)
    forged["entries"][0]["pool_id"] = "training_support:9999"
    forged["manifest_sha256"] = review._json_digest(  # type: ignore[attr-defined]
        {key: value for key, value in forged.items() if key != "manifest_sha256"}
    )
    with pytest.raises(ValueError):
        review.review_selected_manifest(forged, eligible_entries=eligible)
