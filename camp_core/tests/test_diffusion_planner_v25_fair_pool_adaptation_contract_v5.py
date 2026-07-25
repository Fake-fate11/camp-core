from __future__ import annotations

from copy import deepcopy
import hashlib
import inspect
import sys
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_adaptation_contract_v4 as v4,
)
from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_adaptation_contract_v5 as v5,
)
from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_adaptation_review_v4 as v4_review,
)
from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_adaptation_review_v5 as v5_review,
)
from camp_core.integrations.diffusion_planner_v25_fair_pool_adaptation_contract_v2 import (
    bootstrap_upper_threshold,
    sha256_json,
)


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
import test_diffusion_planner_v25_fair_pool_adaptation_contract_v4 as t4  # noqa: E402


SELECTOR_SOURCE_SHA = hashlib.sha256(
    b"synthetic-v5-selector-source"
).hexdigest()


def _array_sha(value: np.ndarray) -> str:
    return hashlib.sha256(
        np.ascontiguousarray(value.astype("<f8", copy=False)).tobytes(
            order="C"
        )
    ).hexdigest()


def _semantic_run(
    row: dict[str, object],
    *,
    state_index: int,
) -> tuple[dict[str, object], dict[str, object]]:
    mode_index = v4.MODES.index(row["mode"])
    repeat = int(row["repeat_index"])
    candidate = t4._candidate(state_index, repeat)
    neighbor = candidate[:, None, :, :].copy()
    neighbor[:, 0, :, 0] += 10.0
    atoms = np.empty((8, 14), dtype=np.float64)
    for candidate_index in range(8):
        atoms[candidate_index] = (
            np.arange(14, dtype=np.float64)
            + candidate_index * 0.01
            + repeat * 2e-6
            + mode_index * 3e-6
            + state_index * 1e-9
        )
    candidate_sha, row_sha = t4._tensor_hashes(candidate)
    neighbor_sha = _array_sha(neighbor)
    atom_sha = _array_sha(atoms)
    forward_preimage = {
        "state_spec_id": row["state_spec_id"],
        "mode": row["mode"],
        "repeat_index": repeat,
        "input_manifest_sha256": row["input_manifest_sha256"],
        "actual_state_sha256": row["actual_state_sha256"],
        "actual_latent_manifest_sha256": row[
            "actual_latent_manifest_sha256"
        ],
        "fixed_dp_head": row["fixed_dp_head"],
        "checkpoint_sha256": row["checkpoint_sha256"],
        "model_source_sha256": row["model_source_sha256"],
        "selector_source_sha256": SELECTOR_SOURCE_SHA,
        "model_call_count": row["model_call_count"],
        "candidate_tensor_sha256": candidate_sha,
        "candidate_row_sha256": row_sha,
        "neighbor_tensor_sha256": neighbor_sha,
        "atom_tensor_sha256": atom_sha,
    }
    forward_sha = sha256_json(forward_preimage)
    pool_sha = sha256_json(
        {
            "forward_binding_sha256": forward_sha,
            "candidate_tensor_sha256": candidate_sha,
        }
    )
    forward = {
        **forward_preimage,
        "forward_binding_sha256": forward_sha,
        "forward_invocation_id": f"forward:{forward_sha}",
        "pool_binding_sha256": pool_sha,
        "pool_id": f"pool:{pool_sha}",
    }
    row["forward_invocation_id"] = forward["forward_invocation_id"]
    row["pool_id"] = forward["pool_id"]
    row["candidate_tensor_sha256"] = candidate_sha
    row["candidate_row_sha256"] = row_sha
    row["all_finite"] = True
    payload = dict(row)
    payload.pop("receipt_sha256")
    row["receipt_sha256"] = sha256_json(payload)
    selectors = {}
    checked_selectors = {}
    for arm_index, arm in enumerate(v4.ARMS):
        scores = [
            float(index)
            + repeat * 4e-6
            + mode_index * 5e-6
            + arm_index * 0.1
            for index in range(8)
        ]
        mask = [True] * 8
        selector = {
            "arm": arm,
            "state_spec_id": row["state_spec_id"],
            "mode": row["mode"],
            "selector_source_sha256": SELECTOR_SOURCE_SHA,
            "pool_id": forward["pool_id"],
            "candidate_tensor_sha256": candidate_sha,
            "pre_tensor_sha256": candidate_sha,
            "post_tensor_sha256": candidate_sha,
            "scores": scores,
            "mask": mask,
            "selected_index": 0,
            "selected_action": v5.encode_array_blob(candidate[0]),
            "executable": "executable",
            "terminal": "complete",
            "dp_model_call_count_after_pool": 0,
            "latent_replacement_count_after_pool": 0,
            "candidate_generation_count_after_pool": 0,
        }
        selector["selector_receipt_sha256"] = sha256_json(selector)
        selectors[arm] = selector
        checked_selectors[arm] = {
            "scores": scores,
            "mask": mask,
            "selected_index": 0,
            "selected_action": candidate[0],
            "executable": "executable",
            "terminal": "complete",
        }
    semantic = {
        "schema_version": v5.SEMANTIC_RUN_SCHEMA,
        "state_spec_id": row["state_spec_id"],
        "mode": row["mode"],
        "repeat_index": repeat,
        "v4_run_receipt_sha256": row["receipt_sha256"],
        "forward_binding": forward,
        "candidate_ego_trajectory": v5.encode_array_blob(candidate),
        "candidate_neighbor_trajectory": v5.encode_array_blob(neighbor),
        "neighbor_actor_fingerprints": [
            hashlib.sha256(b"synthetic-neighbor-0").hexdigest()
        ],
        "atom_vectors": v5.encode_array_blob(atoms),
        "selectors": selectors,
    }
    semantic["semantic_receipt_sha256"] = sha256_json(semantic)
    checked = {
        "state_spec_id": row["state_spec_id"],
        "mode": row["mode"],
        "repeat_index": repeat,
        "v4_run_receipt_sha256": row["receipt_sha256"],
        "candidate": candidate,
        "neighbor": neighbor,
        "neighbor_actor_fingerprints": semantic[
            "neighbor_actor_fingerprints"
        ],
        "atoms": atoms,
        "scores": {
            arm: checked_selectors[arm]["scores"] for arm in v4.ARMS
        },
        "masks": {
            arm: checked_selectors[arm]["mask"] for arm in v4.ARMS
        },
        "selectors": checked_selectors,
        "candidate_sha256": candidate_sha,
        "row_sha256": row_sha,
        "forward_invocation_id": forward["forward_invocation_id"],
        "pool_id": forward["pool_id"],
    }
    return semantic, checked


def _update_runs_and_semantics(
    payload: dict[str, object],
) -> tuple[list[dict[str, object]], dict[tuple[str, str, int], dict[str, object]]]:
    semantic_rows = []
    checked = {}
    for row in payload["run_receipts"]:
        state_index = int(str(row["state_spec_id"]).rsplit(":", 1)[1])
        semantic, decoded = _semantic_run(row, state_index=state_index)
        semantic_rows.append(semantic)
        checked[
            (row["mode"], row["state_spec_id"], row["repeat_index"])
        ] = decoded
    run_map = {
        (row["mode"], row["state_spec_id"], row["repeat_index"]): row
        for row in payload["run_receipts"]
    }
    for pair in payload["pair_receipts"]:
        if pair["phase"] == "cross_mode":
            left_mode, right_mode = v4.MODES
        else:
            left_mode = right_mode = v4.MODE_BY_PHASE[pair["phase"]]
        pair["left_run_receipt_sha256"] = run_map[
            (
                left_mode,
                pair["state_spec_id"],
                pair["left_repeat_index"],
            )
        ]["receipt_sha256"]
        pair["right_run_receipt_sha256"] = run_map[
            (
                right_mode,
                pair["state_spec_id"],
                pair["right_repeat_index"],
            )
        ]["receipt_sha256"]
    return semantic_rows, checked


def _update_repeat0_hard(
    payload: dict[str, object],
    checked: dict[tuple[str, str, int], dict[str, object]],
) -> None:
    run_map = {
        (row["mode"], row["state_spec_id"], row["repeat_index"]): row
        for row in payload["run_receipts"]
    }
    for hard in payload["hard_state_receipts"]:
        state_id = hard["state_spec_id"]
        for mode in v4.MODES:
            run = run_map[(mode, state_id, 0)]
            semantic = checked[(mode, state_id, 0)]
            pool = hard["candidate_pools"][mode]
            pool.update(
                {
                    "run_receipt_sha256": run["receipt_sha256"],
                    "forward_invocation_id": semantic[
                        "forward_invocation_id"
                    ],
                    "pool_id": semantic["pool_id"],
                    "tensor_sha256": semantic["candidate_sha256"],
                    "row_sha256": semantic["row_sha256"],
                    "candidate_tensor": semantic["candidate"].tolist(),
                }
            )
            for arm in v4.ARMS:
                source = hard["selectors"][arm][mode]
                expected = semantic["selectors"][arm]
                source.update(
                    {
                        "pool_id": semantic["pool_id"],
                        "candidate_tensor_sha256": semantic[
                            "candidate_sha256"
                        ],
                        "pre_tensor_sha256": semantic[
                            "candidate_sha256"
                        ],
                        "post_tensor_sha256": semantic[
                            "candidate_sha256"
                        ],
                        "scores": expected["scores"],
                        "mask": expected["mask"],
                        "selected_index": expected["selected_index"],
                        "selected_action_80x4": expected[
                            "selected_action"
                        ].tolist(),
                    }
                )
                source_payload = dict(source)
                source_payload.pop("receipt_sha256")
                source["receipt_sha256"] = sha256_json(source_payload)
        hard_payload = dict(hard)
        hard_payload.pop("receipt_sha256")
        hard["receipt_sha256"] = sha256_json(hard_payload)


def _state_thresholds(
    runs: dict[tuple[str, str, int], dict[str, object]],
    pairs: list[dict[str, object]],
) -> dict[tuple[str, str, str], float]:
    base = v5._base_values_by_pair(runs, pairs)
    thresholds = {}
    states = sorted({row["state_spec_id"] for row in pairs})
    for phase, mode in (
        ("sequential_within", v4.MODES[0]),
        ("batch8_within", v4.MODES[1]),
    ):
        for endpoint in v4.WITHIN_NUMERIC_IDS:
            statistics = []
            for state in states:
                values = [
                    base[(phase, state, row["pair_index"])][endpoint]
                    for row in pairs
                    if row["phase"] == phase
                    and row["state_spec_id"] == state
                ]
                statistics.append(max(values))
            thresholds[(phase, mode, endpoint)] = bootstrap_upper_threshold(
                statistics,
                resolution_floor=v4._resolution_floor(endpoint),
            )
    return thresholds


def _set_pair_cache(
    pairs: list[dict[str, object]],
    runs: dict[tuple[str, str, int], dict[str, object]],
    thresholds: dict[tuple[str, str, str], float],
) -> None:
    expected = v5.derive_pair_cache_v5(
        runs, pairs, within_thresholds=thresholds
    )
    for row in pairs:
        identity = (row["phase"], row["state_spec_id"], row["pair_index"])
        row["endpoint_values"] = expected[identity]
        payload = dict(row)
        payload.pop("receipt_sha256")
        row["receipt_sha256"] = sha256_json(payload)


def _reseal_review(
    source: dict[str, object], review: dict[str, object]
) -> None:
    t4._reseal_artifact(source)
    review["payload"]["source_root_sha256"] = source["root_sha256"]
    review["payload"]["source_payload_sha256"] = source["payload_sha256"]
    t4._reseal_artifact(review)


def _rebuild_v4_chain(
    chain: dict[str, object],
    *,
    calibration_checked: dict[tuple[str, str, int], dict[str, object]],
    validation_checked: dict[tuple[str, str, int], dict[str, object]],
) -> None:
    package = chain["package"]
    artifacts = package["artifacts"]
    calibration = artifacts["calibration_receipts"]
    calibration_review = artifacts["calibration_receipts_review"]
    thresholds = _state_thresholds(
        calibration_checked, calibration["payload"]["pair_receipts"]
    )
    _set_pair_cache(
        calibration["payload"]["pair_receipts"],
        calibration_checked,
        thresholds,
    )
    _reseal_review(calibration, calibration_review)
    freeze = artifacts["threshold_freeze"]
    freeze["payload"] = t4._freeze_payload(
        contract=chain["contract"],
        contract_root=chain["anchor"]["contract_root_sha256"],
        authority_root=artifacts["acquisition_authority"]["root_sha256"],
        calibration_root=calibration["root_sha256"],
        calibration_review_root=calibration_review["root_sha256"],
        calibration_specs=chain["contract"]["inherited_v3_contract"][
            "state_specifications"
        ]["development_calibration"],
        calibration_pair_rows=calibration["payload"]["pair_receipts"],
    )
    _reseal_review(freeze, artifacts["threshold_freeze_review"])
    validation = artifacts["validation_receipts"]
    validation["payload"]["threshold_freeze_root_sha256"] = freeze[
        "root_sha256"
    ]
    validation["payload"][
        "threshold_freeze_review_root_sha256"
    ] = artifacts["threshold_freeze_review"]["root_sha256"]
    _set_pair_cache(
        validation["payload"]["pair_receipts"],
        validation_checked,
        thresholds,
    )
    _reseal_review(validation, artifacts["validation_receipts_review"])
    old_anchor = chain["anchor"]
    chain["anchor"] = v4.make_trust_anchor(
        chain["contract"],
        contract_root_sha256=old_anchor["contract_root_sha256"],
        contract_review_root_sha256=old_anchor[
            "contract_review_root_sha256"
        ],
        input_manifest_authority_root_sha256=old_anchor[
            "input_manifest_authority_root_sha256"
        ],
        artifact_roots={
            name: artifacts[name]["root_sha256"] for name in v4.ARTIFACT_NAMES
        },
        high_decision_sha256=old_anchor["high_decision_sha256"],
    )
    package["trust_anchor_root_sha256"] = chain["anchor"][
        "trust_anchor_root_sha256"
    ]


@pytest.fixture(scope="module")
def synthetic_chain() -> dict[str, object]:
    monkeypatch = pytest.MonkeyPatch()
    try:
        base = t4.synthetic_chain.__wrapped__(monkeypatch)
        calibration_payload = base["package"]["artifacts"][
            "calibration_receipts"
        ]["payload"]
        validation_payload = base["package"]["artifacts"][
            "validation_receipts"
        ]["payload"]
        calibration_semantics, calibration_checked = (
            _update_runs_and_semantics(calibration_payload)
        )
        validation_semantics, validation_checked = (
            _update_runs_and_semantics(validation_payload)
        )
        _update_repeat0_hard(validation_payload, validation_checked)
        _rebuild_v4_chain(
            base,
            calibration_checked=calibration_checked,
            validation_checked=validation_checked,
        )
        contract = v5.adaptation_contract_v5()
        monkeypatch.setattr(
            v5_review,
            "EXPECTED_PAYLOAD_SHA256",
            contract["contract_payload_sha256"],
        )
        monkeypatch.setattr(
            v5_review,
            "EXPECTED_V4_PAYLOAD_SHA256",
            base["contract"]["contract_payload_sha256"],
        )
        semantic_artifacts = {}
        for split, rows, source_name, review_name, v4_name in (
            (
                "development_calibration",
                calibration_semantics,
                "calibration_semantic_receipts",
                "calibration_semantic_receipts_review",
                "calibration_receipts",
            ),
            (
                "independent_validation",
                validation_semantics,
                "validation_semantic_receipts",
                "validation_semantic_receipts_review",
                "validation_receipts",
            ),
        ):
            source = v5.make_semantic_artifact(
                v5.SEMANTIC_ARTIFACT_KIND[source_name],
                {
                    "schema_version": v5.SEMANTIC_RECEIPT_SCHEMA,
                    "split": split,
                    "v4_receipts_root_sha256": base["package"][
                        "artifacts"
                    ][v4_name]["root_sha256"],
                    "run_count": 640,
                    "run_semantics": rows,
                },
            )
            review = v5.make_semantic_review(
                source,
                review_kind=v5.SEMANTIC_ARTIFACT_KIND[review_name],
            )
            semantic_artifacts[source_name] = source
            semantic_artifacts[review_name] = review
        anchor = v5.make_trust_anchor_v5(
            contract,
            contract_root_sha256="1" * 64,
            contract_review_root_sha256="2" * 64,
            v4_trust_anchor_root_sha256=base["anchor"][
                "trust_anchor_root_sha256"
            ],
            selector_source_sha256=SELECTOR_SOURCE_SHA,
            semantic_artifact_roots={
                name: semantic_artifacts[name]["root_sha256"]
                for name in v5.SEMANTIC_ARTIFACT_NAMES
            },
            high_decision_sha256="3" * 64,
        )
        package = {
            "schema_version": v5.QUALIFICATION_PACKAGE_SCHEMA,
            "contract_payload_sha256": contract["contract_payload_sha256"],
            "trust_anchor_root_sha256": anchor[
                "trust_anchor_root_sha256"
            ],
            "v4_package": base["package"],
            "v4_trust_anchor": base["anchor"],
            "semantic_artifacts": semantic_artifacts,
        }
        yield {
            "contract": contract,
            "package": package,
            "anchor": anchor,
        }
    finally:
        monkeypatch.undo()


def _reseal_outer(chain: dict[str, object]) -> None:
    semantic = chain["package"]["semantic_artifacts"]
    for source_name, review_name in (
        (
            "calibration_semantic_receipts",
            "calibration_semantic_receipts_review",
        ),
        (
            "validation_semantic_receipts",
            "validation_semantic_receipts_review",
        ),
    ):
        _reseal_review(semantic[source_name], semantic[review_name])
    chain["anchor"]["v4_trust_anchor_root_sha256"] = chain["package"][
        "v4_trust_anchor"
    ]["trust_anchor_root_sha256"]
    chain["anchor"]["semantic_artifact_roots"] = {
        name: semantic[name]["root_sha256"]
        for name in v5.SEMANTIC_ARTIFACT_NAMES
    }
    payload = dict(chain["anchor"])
    payload.pop("trust_anchor_root_sha256")
    chain["anchor"]["trust_anchor_root_sha256"] = sha256_json(payload)
    chain["package"]["trust_anchor_root_sha256"] = chain["anchor"][
        "trust_anchor_root_sha256"
    ]


def test_contract_v5_is_design_only_and_raw_semantic(
    synthetic_chain: dict[str, object],
) -> None:
    contract = v5.validate_contract_v5(synthetic_chain["contract"])
    assert contract["decision"]["acquisition_authorized"] is False
    assert contract["endpoint_derivation"]["phase_key_count"] == 73
    assert (
        contract["endpoint_derivation"]["endpoint_values_role"]
        == "derived_cache_only"
    )
    assert contract["raw_semantic_run_receipt"][
        "all_five_repeats_require_raw_candidate_and_selector_preimages"
    ] is True


def test_complete_trusted_raw_semantic_chain_passes_both_oracles(
    synthetic_chain: dict[str, object],
) -> None:
    decision = v5.decide_qualification_v5(
        synthetic_chain["contract"],
        synthetic_chain["package"],
        trust_anchor=synthetic_chain["anchor"],
        expected_trust_anchor_root_sha256=synthetic_chain["anchor"][
            "trust_anchor_root_sha256"
        ],
    )
    assert decision["status"] == "PASS"
    assert decision["raw_semantic_run_receipt_count"] == 1280
    assert decision["numeric_phase_key_count_reconstructed"] == 73
    assert decision["endpoint_values_used_as_authority"] is False
    reviewed = v5_review.literal_decide_qualification_v5(
        synthetic_chain["contract"],
        synthetic_chain["package"],
        trust_anchor=synthetic_chain["anchor"],
        expected_trust_anchor_root_sha256=synthetic_chain["anchor"][
            "trust_anchor_root_sha256"
        ],
    )
    assert reviewed == decision


def test_all_numeric_caches_zero_resealed_and_retrusted_still_blocks(
    synthetic_chain: dict[str, object],
) -> None:
    chain = deepcopy(synthetic_chain)
    v4_package = chain["package"]["v4_package"]
    artifacts = v4_package["artifacts"]
    for name in ("calibration_receipts", "validation_receipts"):
        for pair in artifacts[name]["payload"]["pair_receipts"]:
            pair["endpoint_values"] = {
                endpoint: 0.0
                for endpoint in pair["endpoint_values"]
            }
            payload = dict(pair)
            payload.pop("receipt_sha256")
            pair["receipt_sha256"] = sha256_json(payload)
    calibration = artifacts["calibration_receipts"]
    _reseal_review(calibration, artifacts["calibration_receipts_review"])
    freeze = artifacts["threshold_freeze"]
    freeze["payload"] = t4._freeze_payload(
        contract=chain["contract"]["inherited_v4_contract"],
        contract_root=chain["package"]["v4_trust_anchor"][
            "contract_root_sha256"
        ],
        authority_root=artifacts["acquisition_authority"]["root_sha256"],
        calibration_root=calibration["root_sha256"],
        calibration_review_root=artifacts[
            "calibration_receipts_review"
        ]["root_sha256"],
        calibration_specs=chain["contract"]["inherited_v4_contract"][
            "inherited_v3_contract"
        ]["state_specifications"]["development_calibration"],
        calibration_pair_rows=calibration["payload"]["pair_receipts"],
    )
    _reseal_review(freeze, artifacts["threshold_freeze_review"])
    validation = artifacts["validation_receipts"]
    validation["payload"]["threshold_freeze_root_sha256"] = freeze[
        "root_sha256"
    ]
    validation["payload"][
        "threshold_freeze_review_root_sha256"
    ] = artifacts["threshold_freeze_review"]["root_sha256"]
    _reseal_review(validation, artifacts["validation_receipts_review"])
    old = chain["package"]["v4_trust_anchor"]
    chain["package"]["v4_trust_anchor"] = v4.make_trust_anchor(
        chain["contract"]["inherited_v4_contract"],
        contract_root_sha256=old["contract_root_sha256"],
        contract_review_root_sha256=old["contract_review_root_sha256"],
        input_manifest_authority_root_sha256=old[
            "input_manifest_authority_root_sha256"
        ],
        artifact_roots={
            name: artifacts[name]["root_sha256"] for name in v4.ARTIFACT_NAMES
        },
        high_decision_sha256=old["high_decision_sha256"],
    )
    v4_package["trust_anchor_root_sha256"] = chain["package"][
        "v4_trust_anchor"
    ]["trust_anchor_root_sha256"]
    semantic = chain["package"]["semantic_artifacts"]
    semantic["calibration_semantic_receipts"]["payload"][
        "v4_receipts_root_sha256"
    ] = calibration["root_sha256"]
    semantic["validation_semantic_receipts"]["payload"][
        "v4_receipts_root_sha256"
    ] = validation["root_sha256"]
    _reseal_outer(chain)
    with pytest.raises(ValueError, match="raw preimage|raw-semantic"):
        v5.decide_qualification_v5(
            chain["contract"],
            chain["package"],
            trust_anchor=chain["anchor"],
            expected_trust_anchor_root_sha256=chain["anchor"][
                "trust_anchor_root_sha256"
            ],
        )
    with pytest.raises(ValueError, match="raw/cache"):
        v5_review.literal_decide_qualification_v5(
            chain["contract"],
            chain["package"],
            trust_anchor=chain["anchor"],
            expected_trust_anchor_root_sha256=chain["anchor"][
                "trust_anchor_root_sha256"
            ],
        )


@pytest.mark.parametrize("repeat_index", (1, 2, 3, 4))
def test_repeat1_through_4_tensor_reseal_and_retrust_blocks(
    synthetic_chain: dict[str, object],
    repeat_index: int,
) -> None:
    chain = deepcopy(synthetic_chain)
    source = chain["package"]["semantic_artifacts"][
        "calibration_semantic_receipts"
    ]
    row = next(
        item
        for item in source["payload"]["run_semantics"]
        if item["repeat_index"] == repeat_index
    )
    candidate = v5._array_blob(
        row["candidate_ego_trajectory"], expected_shape=(8, 80, 4)
    )
    candidate[7, 79, 0] += 0.25
    row["candidate_ego_trajectory"] = v5.encode_array_blob(candidate)
    payload = dict(row)
    payload.pop("semantic_receipt_sha256")
    row["semantic_receipt_sha256"] = sha256_json(payload)
    _reseal_outer(chain)
    with pytest.raises(ValueError, match="forward/pool raw semantic binding"):
        v5.decide_qualification_v5(
            chain["contract"],
            chain["package"],
            trust_anchor=chain["anchor"],
            expected_trust_anchor_root_sha256=chain["anchor"][
                "trust_anchor_root_sha256"
            ],
        )
    with pytest.raises(ValueError, match="forward/pool binding"):
        v5_review.literal_decide_qualification_v5(
            chain["contract"],
            chain["package"],
            trust_anchor=chain["anchor"],
            expected_trust_anchor_root_sha256=chain["anchor"][
                "trust_anchor_root_sha256"
            ],
        )


def test_well_formed_but_untrusted_semantic_root_blocks(
    synthetic_chain: dict[str, object],
) -> None:
    package = deepcopy(synthetic_chain["package"])
    package["semantic_artifacts"]["validation_semantic_receipts"][
        "root_sha256"
    ] = "f" * 64
    with pytest.raises(ValueError, match="semantic content artifact root"):
        v5.decide_qualification_v5(
            synthetic_chain["contract"],
            package,
            trust_anchor=synthetic_chain["anchor"],
            expected_trust_anchor_root_sha256=synthetic_chain["anchor"][
                "trust_anchor_root_sha256"
            ],
        )


def test_reviewer_has_local_semantic_oracle() -> None:
    source = inspect.getsource(v5_review)
    assert "fair_pool_adaptation_contract_v5 import" not in source
    assert "selector import" not in source
    assert "fair_nonholdout import" not in source
    assert "bootstrap_upper_threshold" not in source
    assert "spearman_rank_error" not in source
    assert "ATOM_SCALES = (" in source
    assert "def _bootstrap(" in source
    assert "def _rank_error(" in source
