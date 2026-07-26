from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations import (
    diffusion_planner_v25_selector_after_pool_replay as producer,
)
from camp_core.integrations import (
    diffusion_planner_v25_selector_after_pool_replay_review as reviewer,
)


def _sources() -> dict[str, str]:
    return {
        name: hashlib.sha256(name.encode("ascii")).hexdigest()
        for name in (
            "contract_module",
            "contract_reviewer",
            "contract_freezer",
            "contract_review_runner",
            "preflight_producer",
            "preflight_reviewer",
            "replay_producer",
            "replay_reviewer",
        )
    }


def _contract() -> dict:
    return producer.contract(
        implementation_head="1" * 40,
        source_hashes=_sources(),
    )


def _rehash(value: dict) -> None:
    payload = dict(value)
    payload.pop("contract_payload_sha256", None)
    value["contract_payload_sha256"] = producer.sha256_json(payload)


def _selection_inputs() -> dict:
    candidates = np.zeros((8, 80, 4), dtype="<f4")
    candidates[:, :, 0] = np.arange(8, dtype=np.float32)[:, None]
    atoms = np.tile(np.arange(8, dtype=np.float64)[:, None], (1, 14))
    scales = np.ones(14, dtype=np.float64)
    weights = np.full(14, 1.0 / 14.0, dtype=np.float64)
    mask = np.ones(8, dtype=np.bool_)
    return {
        "candidates": candidates,
        "raw_atoms": atoms,
        "scales": scales,
        "weights": weights,
        "eligibility_mask": mask,
    }


def test_contract_and_independent_review_pass() -> None:
    value = _contract()
    assert producer.validate_contract(value) == value
    assert reviewer.review_contract(value) == value
    assert value["denominator"]["run_count"] == 320
    assert value["runtime_gates"]["model_calls"] == 0
    assert value["atoms"]["count"] == 14


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("selection", "tie_break"), "highest_index"),
        (("selection", "score_direction"), "higher_is_better"),
        (("denominator", "run_count"), 319),
        (("runtime_gates", "model_calls"), 1),
        (("runtime_gates", "candidate0_is_row0"), False),
        (
            (
                "interpretation",
                "benefit_or_closed_loop_effect_claimed",
            ),
            True,
        ),
    ],
)
def test_semantic_mutation_resealed_is_rejected(
    path: tuple[str, str], replacement: object
) -> None:
    value = deepcopy(_contract())
    value[path[0]][path[1]] = replacement
    _rehash(value)
    with pytest.raises(ValueError):
        producer.validate_contract(value)
    with pytest.raises(ValueError):
        reviewer.review_contract(value)


def test_unknown_or_missing_atom_resealed_is_rejected() -> None:
    for mutate in ("missing", "unknown"):
        value = deepcopy(_contract())
        if mutate == "missing":
            value["atoms"]["registry"].pop()
        else:
            value["atoms"]["registry"].append(
                {
                    "index": "14",
                    "name": "unknown",
                    "units": "x",
                    "formula": "x",
                    "source": "x",
                    "applicability": "x",
                    "scale_source": "x",
                }
            )
        _rehash(value)
        with pytest.raises(ValueError):
            producer.validate_contract(value)
        with pytest.raises(ValueError):
            reviewer.review_contract(value)


def test_causal_inverse_transform_is_exact_and_finite() -> None:
    arrays = {}
    for name in producer.MODEL_INPUT_TENSOR_ORDER:
        arrays[name] = np.zeros((1,), dtype=np.float32)
    heading = np.linspace(-2.5, 2.5, 31, dtype=np.float32)
    ego = np.zeros((1, 31, 4), dtype=np.float32)
    ego[0, :, 0] = np.arange(31)
    ego[0, :, 2] = np.cos(heading)
    ego[0, :, 3] = np.sin(heading)
    goal_heading = np.float32(-2.2)
    goal = np.array(
        [[[1.0, 2.0, np.cos(goal_heading), np.sin(goal_heading)]]],
        dtype=np.float32,
    ).reshape(1, 4)
    arrays.update(
        {
            "delay": np.zeros((1,), dtype=np.int64),
            "ego_agent_past": ego,
            "ego_current_state": np.zeros((1, 10), dtype=np.float32),
            "ego_shape": np.ones((1, 3), dtype=np.float32),
            "goal_pose": goal,
            "lanes": np.zeros((1, 140, 20, 33), dtype=np.float32),
            "lanes_has_speed_limit": np.zeros(
                (1, 140, 1), dtype=np.bool_
            ),
            "lanes_speed_limit": np.ones(
                (1, 140, 1), dtype=np.float32
            ),
            "line_strings": np.zeros((1, 60, 20, 4), dtype=np.float32),
            "neighbor_agents_past": np.zeros(
                (1, 320, 31, 11), dtype=np.float32
            ),
            "polygons": np.zeros((1, 10, 40, 3), dtype=np.float32),
            "route_lanes": np.zeros((1, 25, 20, 33), dtype=np.float32),
            "route_lanes_has_speed_limit": np.zeros(
                (1, 25, 1), dtype=np.bool_
            ),
            "route_lanes_speed_limit": np.ones(
                (1, 25, 1), dtype=np.float32
            ),
            "sampled_trajectories": np.zeros(
                (1, 321, 81, 4), dtype=np.float32
            ),
            "static_objects": np.zeros((1, 5, 10), dtype=np.float32),
            "turn_indicators": np.zeros((1, 31), dtype=np.int64),
        }
    )
    result = producer.causal_input_from_model_input(arrays)
    assert result["ego_agent_past"].shape == (31, 3)
    assert np.allclose(result["ego_agent_past"][:, 2], heading, atol=1e-6)
    assert result["goal_pose"].shape == (3,)
    assert np.isclose(result["goal_pose"][2], goal_heading, atol=1e-6)
    assert result["neighbor_agents_past"].shape == (32, 31, 11)
    assert result["turn_indicators"].dtype == np.int32
    assert result["version"].dtype == np.int64


def test_causal_inverse_applies_frozen_normalizer_and_preserves_zero_rows() -> None:
    arrays = {}
    for name in producer.MODEL_INPUT_TENSOR_ORDER:
        arrays[name] = np.zeros((1,), dtype=np.float32)
    arrays.update(
        {
            "delay": np.zeros((1,), dtype=np.int64),
            "ego_agent_past": np.zeros((1, 31, 4), dtype=np.float32),
            "ego_current_state": np.zeros((1, 10), dtype=np.float32),
            "ego_shape": np.ones((1, 3), dtype=np.float32),
            "goal_pose": np.zeros((1, 4), dtype=np.float32),
            "lanes": np.zeros((1, 140, 20, 33), dtype=np.float32),
            "lanes_has_speed_limit": np.zeros((1, 140, 1), dtype=np.bool_),
            "lanes_speed_limit": np.ones((1, 140, 1), dtype=np.float32),
            "line_strings": np.zeros((1, 60, 20, 4), dtype=np.float32),
            "neighbor_agents_past": np.zeros(
                (1, 320, 31, 11), dtype=np.float32
            ),
            "polygons": np.zeros((1, 10, 40, 3), dtype=np.float32),
            "route_lanes": np.zeros((1, 25, 20, 33), dtype=np.float32),
            "route_lanes_has_speed_limit": np.zeros(
                (1, 25, 1), dtype=np.bool_
            ),
            "route_lanes_speed_limit": np.ones(
                (1, 25, 1), dtype=np.float32
            ),
            "sampled_trajectories": np.zeros(
                (1, 321, 81, 4), dtype=np.float32
            ),
            "static_objects": np.zeros((1, 5, 10), dtype=np.float32),
            "turn_indicators": np.zeros((1, 31), dtype=np.int64),
        }
    )
    arrays["ego_current_state"][0, 0] = 2.0
    normalization = {
        "ego_current_state": {
            "mean": [1.0] * 10,
            "std": [3.0] * 10,
        }
    }
    result = producer.causal_input_from_model_input(
        arrays, normalization=normalization
    )
    assert result["ego_current_state"][0] == 7.0
    assert np.all(result["ego_current_state"][1:] == 0.0)


def test_producer_and_reviewer_literal_selection_exact() -> None:
    inputs = _selection_inputs()
    actual = producer.selection_from_preimages(**inputs)
    independent = reviewer.literal_selection(**inputs)
    assert actual == independent
    assert actual["selected_index"] == 0
    assert actual["tie_set"] == [0]
    assert actual["margin"]["value"] == 1.0


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("formula", "forged_formula"),
        ("units", "forged_units"),
        ("source", "forged_source"),
        ("applicability", "forged_applicability"),
    ],
)
def test_atom_semantic_mutation_resealed_is_rejected(
    field: str, replacement: str
) -> None:
    value = deepcopy(_contract())
    value["atoms"]["registry"][8][field] = replacement
    _rehash(value)
    with pytest.raises(ValueError):
        producer.validate_contract(value)
    with pytest.raises(ValueError):
        reviewer.review_contract(value)


def test_exact_tie_uses_lowest_eligible_index() -> None:
    inputs = _selection_inputs()
    inputs["raw_atoms"][1] = inputs["raw_atoms"][0]
    actual = producer.selection_from_preimages(**inputs)
    assert actual["tie_set"] == [0, 1]
    assert actual["selected_index"] == 0
    assert actual["margin"]["value"] == 0.0


def test_empty_or_forged_mask_and_action_binding_fail_closed() -> None:
    inputs = _selection_inputs()
    inputs["eligibility_mask"][:] = False
    with pytest.raises(ValueError):
        producer.selection_from_preimages(**inputs)
    inputs = _selection_inputs()
    result = producer.selection_from_preimages(**inputs)
    forged = np.ascontiguousarray(inputs["candidates"][1])
    assert result["selected_action_sha256"] != producer.array_sha256(forged)


def test_same_state_repeat_determinism_rejects_single_field_drift() -> None:
    base = {
        "status": "computed",
        "candidate_tensor_sha256_before": "a",
        "candidate_tensor_sha256_after": "a",
        "neighbor_tensor_sha256_before": "b",
        "neighbor_tensor_sha256_after": "b",
        "atom_receipt_sha256": "c",
        "context_receipt_sha256": "d",
        "static14d": {"selected_index": 0},
        "scene14d": {"selected_index": 1},
    }
    rows = [deepcopy(base) for _ in range(5)]
    producer.assert_same_state_determinism(rows)
    reviewer.verify_same_state(rows)
    rows[4]["scene14d"]["selected_index"] = 2
    with pytest.raises(ValueError):
        producer.assert_same_state_determinism(rows)
    with pytest.raises(ValueError):
        reviewer.verify_same_state(rows)


def _literal_reviewer_fixture() -> tuple[np.ndarray, np.ndarray, dict]:
    candidates = np.zeros((8, 80, 4), dtype="<f4")
    time = np.arange(80, dtype=np.float32) * np.float32(0.1)
    candidates[:, :, 0] = time[None, :] + (
        np.arange(8, dtype=np.float32)[:, None] * np.float32(0.01)
    )
    candidates[:, :, 2] = 1.0
    neighbor = np.zeros((8, 32, 80, 4), dtype="<f4")
    route = np.zeros((25, 20, 33), dtype=np.float32)
    route[0, :, 0] = np.arange(20, dtype=np.float32)
    route[0, :, 4:6] = np.asarray([0.0, 2.0], dtype=np.float32)
    route[0, :, 6:8] = np.asarray([0.0, -2.0], dtype=np.float32)
    causal = {
        "route_lanes": route,
        "route_lanes_speed_limit": np.r_[
            np.float32(20.0), np.zeros(24, dtype=np.float32)
        ].reshape(25, 1),
        "route_lanes_has_speed_limit": np.r_[
            True, np.zeros(24, dtype=np.bool_)
        ].reshape(25, 1),
        "neighbor_agents_past": np.zeros((32, 31, 11), dtype=np.float32),
        "static_objects": np.zeros((5, 10), dtype=np.float32),
        "ego_shape": np.asarray([2.5, 4.5, 2.0], dtype=np.float32),
        "ego_current_state": np.asarray(
            [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            dtype=np.float32,
        ),
    }
    return candidates, neighbor, causal


def test_reviewer_literal_atoms_context_and_scene_weights_are_local() -> None:
    candidates, neighbor, causal = _literal_reviewer_fixture()
    atoms = reviewer.literal_atoms(
        candidates=candidates, neighbor=neighbor, causal=causal
    )
    assert atoms["raw_atoms"].shape == (8, 14)
    assert np.all(np.isfinite(atoms["raw_atoms"]))
    assert np.all(atoms["raw_atoms"] >= 0.0)
    assert atoms["source_valid_mask"].tolist() == [True] * 8
    assert atoms["atom_applicable_mask"][:, 10].tolist() == [False] * 8
    assert atoms["atom_applicable_mask"][:, 12].tolist() == [False] * 8
    context = reviewer.literal_context(
        candidates=candidates,
        causal=causal,
        source_valid_mask=atoms["source_valid_mask"],
    )
    assert context["raw"].shape == (26,)
    assert context["payload"]["raw_context"]["traffic_phase_unknown"] == 1.0
    assert (
        context["payload"]["source_complete"][
            "traffic_signal_phase_remaining_s"
        ]
        is False
    )
    scene = reviewer.literal_scene_weights(
        raw_context=context["raw"],
        source_complete=context["source_complete"],
        q05=np.full(26, -1.0),
        q95=np.full(26, 100.0),
        theta=np.full((14, 53), 1.0 / 14.0),
    )
    assert scene["phi"].shape == (53,)
    assert scene["weights"].shape == (14,)
    assert np.isclose(scene["weights"].sum(), 1.0)


def test_pool_id_recomputed_from_forward_and_tensor_hashes() -> None:
    expected = producer.sha256_json(
        {
            "forward_id": "1" * 64,
            "candidate_tensor_sha256": "2" * 64,
            "neighbor_tensor_sha256": "3" * 64,
        }
    )
    assert (
        producer.pool_id_from_preimages(
            forward_id="1" * 64,
            candidate_tensor_sha256="2" * 64,
            neighbor_tensor_sha256="3" * 64,
        )
        == expected
    )
    with pytest.raises(ValueError):
        producer.pool_id_from_preimages(
            forward_id="not-a-sha",
            candidate_tensor_sha256="2" * 64,
            neighbor_tensor_sha256="3" * 64,
        )


def test_reviewer_slot_authority_rejects_tensor_pool_and_call_forgery() -> None:
    candidates, neighbor, _ = _literal_reviewer_fixture()
    candidate_sha = producer.array_sha256(candidates)
    neighbor_sha = producer.array_sha256(neighbor)
    forward = "1" * 64
    pool = producer.pool_id_from_preimages(
        forward_id=forward,
        candidate_tensor_sha256=candidate_sha,
        neighbor_tensor_sha256=neighbor_sha,
    )
    binding = {
        "slot": 0,
        "run_id": "run-0",
        "state_index": 0,
        "repeat_index": 0,
        "forward_id": forward,
        "pool_id": pool,
    }
    receipt = {
        **binding,
        "status": "computed",
        "candidate_tensor_sha256": candidate_sha,
        "neighbor_tensor_sha256": neighbor_sha,
        "candidate_row_sha256": [
            producer.array_sha256(candidates[index]) for index in range(8)
        ],
        "candidate_tensor_sha256_before": candidate_sha,
        "candidate_tensor_sha256_after": candidate_sha,
        "neighbor_tensor_sha256_before": neighbor_sha,
        "neighbor_tensor_sha256_after": neighbor_sha,
        "formal_model_call_count": 0,
        "dp_call_count": 0,
        "latent_generation_call_count": 0,
        "candidate_generation_call_count": 0,
        "selector_call_count": 2,
    }
    reviewer.validate_slot_authority(
        receipt=receipt,
        binding=binding,
        candidate=candidates,
        neighbor=neighbor,
    )
    attacks = []
    forged_pool = deepcopy(receipt)
    forged_pool["pool_id"] = "2" * 64
    attacks.append((forged_pool, binding, candidates))
    forged_call = deepcopy(receipt)
    forged_call["formal_model_call_count"] = 1
    attacks.append((forged_call, binding, candidates))
    mutated = candidates.copy()
    mutated[0, 0, 0] += np.float32(1.0)
    attacks.append((receipt, binding, mutated))
    forged_repeat = deepcopy(receipt)
    forged_repeat["repeat_index"] = 1
    attacks.append((forged_repeat, binding, candidates))
    for attacked_receipt, attacked_binding, attacked_candidate in attacks:
        with pytest.raises(ValueError):
            reviewer.validate_slot_authority(
                receipt=attacked_receipt,
                binding=attacked_binding,
                candidate=attacked_candidate,
                neighbor=neighbor,
            )


def test_typed_failure_repeat_cannot_be_misclassified_deterministic() -> None:
    rows = [{"status": "typed_failure_retained"} for _ in range(5)]
    with pytest.raises(ValueError):
        producer.assert_same_state_determinism(rows)


def test_explicit_runtime_policy_rejects_wrong_or_old_python() -> None:
    producer.assert_python_runtime(
        executable="/x/python",
        version_info=(3, 12, 3),
        prefix="/x",
        expected_executable="/x/python",
        expected_prefix="/x",
        expected_exact_version=(3, 12, 3),
    )
    with pytest.raises(RuntimeError):
        producer.assert_python_runtime(
            executable="python",
            version_info=(3, 6, 0),
            prefix="/old",
            expected_executable="/x/python",
            expected_prefix="/x",
            expected_exact_version=(3, 12, 3),
        )


def test_new_stage_files_do_not_use_bare_python_invocation() -> None:
    root = Path(__file__).resolve().parents[2]
    names = [
        root / ".codex_tmp_v25_selector_after_pool_source_audit.sh",
        root / ".codex_tmp_v25_selector_tensor_converter_source.sh",
        root
        / "scripts/integrations/"
        "freeze_diffusion_planner_v25_selector_after_pool_replay_contract.py",
        root
        / "scripts/integrations/"
        "review_diffusion_planner_v25_selector_after_pool_replay_contract.py",
        root
        / "scripts/integrations/"
        "materialize_diffusion_planner_v25_selector_after_pool_replay_preflight.py",
        root
        / "scripts/integrations/"
        "review_diffusion_planner_v25_selector_after_pool_replay_preflight.py",
        root
        / "scripts/integrations/"
        "materialize_diffusion_planner_v25_selector_after_pool_replay.py",
        root
        / "scripts/integrations/"
        "review_diffusion_planner_v25_selector_after_pool_replay.py",
    ]
    for path in names:
        text = path.read_text("utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            assert not stripped.startswith("python ")
            assert not stripped.startswith("python3 ")
