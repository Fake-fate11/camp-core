from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib
import json
import shutil
from types import SimpleNamespace

import numpy as np
import pytest

from camp_core.integrations.carla_exact_speed_source import LiftingTolerances
from camp_core.integrations.carla_exact_speed_source import canonical_json_sha256
from camp_core.integrations.diffusion_planner_causal_materializer import (
    CAUSAL_DP_INPUT_SCHEMA,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def _probe():
    return importlib.import_module(
        "scripts.integrations."
        "run_diffusion_planner_dp_camp_v19_carla_candidate_source_probe"
    )


def _capture() -> dict[str, object]:
    frames = [
        {
            "timestamp_us": index * 100_000,
            "ego_state": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "ego_extent": [4.5, 1.8, 1.5],
            "actors": [],
        }
        for index in range(31)
    ]
    samples = [
        {
            "road_id": road,
            "section_id": 0,
            "lane_id": -1,
            "s": s,
            "x": x,
            "y": 0.0,
            "z": 1.0,
            "lane_width": 3.5,
            "is_junction": road == "2",
        }
        for road, s, x in (
            ("1", 5.0, 0.0),
            ("1", 10.0, 5.0),
            ("2", 0.0, 5.0),
            ("2", 5.0, 10.0),
        )
    ]
    corridor = {
        "schema_version": "dp_camp_v20_carla_route_corridor_v1",
        "map_sha256": "a" * 64,
        "route_sample_step_m": 5.0,
        "station_allowance_m": 3.0518578125e-05,
        "contact_tolerance_m": 0.01,
        "route_samples": [
            {
                "road_id": "1",
                "section_id": 0,
                "lane_id": -1,
                "s": 0.0,
                "x": -5.0,
                "y": 0.0,
                "z": 1.0,
                "lane_width": 3.5,
                "is_junction": False,
            },
            *samples,
        ],
        "directed_edges": [(("1", 0, -1), ("2", 0, -1))],
        "identity_directions": [
            [["1", 0, -1], 1],
            [["2", 0, -1], 1],
        ],
        "predecessor_receipt": {
            "predecessor_count": 1,
            "route_step_m": 5.0,
            "identity": ["1", 0, -1],
            "s": 0.0,
        },
        "boundary_receipts": [],
        "max_contact_gap_m": 0.0,
    }
    corridor["corridor_sha256"] = canonical_json_sha256(corridor)

    def route_lane(start_x: float) -> dict[str, list[list[float]]]:
        return {
            "centerline": [[start_x + index, 0.0] for index in range(20)],
            "left_boundary": [[start_x + index, 1.75] for index in range(20)],
            "right_boundary": [[start_x + index, -1.75] for index in range(20)],
        }

    return {
        "schema_version": "dp_camp_v20_carla_source_capture_v1",
        "selection_seed": 3411,
        "map_name": "Town01",
        "map_sha256": "a" * 64,
        "source_head": "b" * 64,
        "decision_timestamp_us": 3_000_000,
        "traffic_timestamp_us": None,
        "traffic_light_state_available": False,
        "route_source": "current_map_topology_successors",
        "route_sample_step_m": 5.0,
        "route_samples": samples,
        "directed_edges": [(("1", 0, -1), ("2", 0, -1))],
        "route_lanes": [route_lane(0.0), route_lane(19.0)],
        "lifting_corridor": corridor,
        "mission_goal_pose": [10.0, 0.0, 0.0],
        "frames": frames,
    }


def _reseal_corridor(capture: dict[str, object]) -> None:
    corridor = capture["lifting_corridor"]
    corridor["corridor_sha256"] = canonical_json_sha256(
        {key: value for key, value in corridor.items() if key != "corridor_sha256"}
    )


def _write_receipt_inputs(tmp_path, capture=None):
    probe = _probe()
    capture = _capture() if capture is None else capture
    xodr = "<OpenDRIVE/>"
    map_sha256 = hashlib.sha256(xodr.encode("utf-8")).hexdigest()
    capture["map_sha256"] = map_sha256
    capture["lifting_corridor"]["map_sha256"] = map_sha256
    _reseal_corridor(capture)
    camp_dir = tmp_path / "camp"
    default_dir = tmp_path / "default"
    context_path = tmp_path / "context.json"
    probe.write_probe_requests(
        capture,
        tolerances=probe.FROZEN_LIFTING_TOLERANCES,
        camp_request_dir=camp_dir,
        default_request_dir=default_dir,
        context_path=context_path,
        camp_head="c" * 40,
        dp_head=FIXED_DP_HEAD,
        selector_hashes=("1" * 64, "2" * 64, "3" * 64),
    )
    return probe, capture, xodr, camp_dir, default_dir, context_path


def _stub_receipt_responses(monkeypatch, probe, camp_dir, provenances=None) -> None:
    monkeypatch.setattr(
        probe,
        "read_response",
        lambda directory, **_kwargs: SimpleNamespace(
            arrays={
                "candidates": np.zeros((8, 80, 4), dtype=np.float32)
                if directory == camp_dir
                else np.zeros((80, 4), dtype=np.float32)
            }
            if directory == camp_dir
            else {"selected_trajectory": np.zeros((80, 4), dtype=np.float32)},
            metadata={
                "candidate_sha256_before": "c" * 64,
                "selected_trajectory_sha256": "d" * 64,
            },
        ),
    )
    monkeypatch.setattr(
        probe,
        "lift_k8_route_receipt",
        lambda **kwargs: (
            provenances.append(kwargs["provenance"]) if provenances is not None else None
        )
        or {},
    )


def _request_evidence(metadata: dict[str, object]) -> dict[str, object]:
    return {
        "causal_input_sha256": metadata["causal_input_sha256"],
        "simulation_time_us": metadata["simulation_time_us"],
        "tick_seed": metadata["tick_seed"],
        "pair_run_key": metadata["pair_run_key"],
        "dp_head": metadata["dp_head"],
        "scenario_token": metadata["scenario_token"],
        "request_metadata_sha256": hashlib.sha256(
            json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }


def test_deterministic_route_rejects_multiple_unseen_successors() -> None:
    left = SimpleNamespace(road_id=1, section_id=0, lane_id=-1, s=5.0)
    right = SimpleNamespace(road_id=2, section_id=0, lane_id=-1, s=5.0)
    start = SimpleNamespace(
        road_id=1,
        section_id=0,
        lane_id=-1,
        s=0.0,
        next=lambda _step: [left, right],
    )
    map_api = SimpleNamespace(generate_waypoints=lambda _step: [start])

    with pytest.raises(ValueError, match="multiple unseen successors"):
        _probe()._deterministic_route(map_api, 5.0, 2)


def test_materialization_keeps_corridor_out_of_fixed_dp_route() -> None:
    capture = _capture()
    dp_route_before = np.asarray(capture["route_lanes"][0]["centerline"]).copy()

    materialized, context, _ = _probe().build_probe_materialization(
        capture,
        tolerances=LiftingTolerances(
            1.5273609989704584,
            3.0518578125e-05,
            1e-9,
            3.0518578125e-05,
        ),
    )

    assert context.samples[0].x < capture["route_samples"][0]["x"]
    np.testing.assert_array_equal(
        materialized.dp_input["route_lanes"][0, : len(dp_route_before), :2],
        dp_route_before,
    )
    assert materialized.metadata["source_metadata"]["lifting_corridor_sha256"] == (
        capture["lifting_corridor"]["corridor_sha256"]
    )


def test_materialization_rejects_corridor_sha_drift() -> None:
    capture = _capture()
    capture["lifting_corridor"]["route_samples"][0]["x"] -= 1.0

    with pytest.raises(ValueError, match="corridor SHA mismatch"):
        _probe().build_probe_materialization(
            capture,
            tolerances=LiftingTolerances(1.5, 1e-6, 1e-6, 1e-6),
        )


@pytest.mark.parametrize("key", ("frames", "unexpected_capture_field"))
def test_materialization_requires_exact_capture_fields(key: str) -> None:
    capture = _capture()
    if key in capture:
        del capture[key]
    else:
        capture[key] = None

    with pytest.raises(ValueError, match="source capture fields"):
        _probe().build_probe_materialization(
            capture,
            tolerances=LiftingTolerances(1.5, 1e-6, 1e-6, 1e-6),
        )


@pytest.mark.parametrize("key", ("boundary_receipts", "unexpected_corridor_field"))
def test_materialization_requires_exact_corridor_fields(key: str) -> None:
    capture = _capture()
    corridor = capture["lifting_corridor"]
    if key in corridor:
        del corridor[key]
    else:
        corridor[key] = None
    _reseal_corridor(capture)

    with pytest.raises(ValueError, match="lifting corridor fields"):
        _probe().build_probe_materialization(
            capture,
            tolerances=LiftingTolerances(1.5, 1e-6, 1e-6, 1e-6),
        )


@pytest.mark.parametrize(
    ("identity", "direction"),
    (
        (["1", 0.0, -1], 1),
        (["1", False, -1], 1),
        (["1", 0, -1.0], 1),
        (["1", 0, -1], True),
        (["1", 0, -1], 1.0),
        (["1", 0, -1], "1"),
    ),
)
def test_materialization_rejects_coerced_corridor_identity_directions(
    identity: list[object], direction: object
) -> None:
    capture = _capture()
    capture["lifting_corridor"]["identity_directions"][0] = [identity, direction]
    _reseal_corridor(capture)

    with pytest.raises(ValueError, match="identity directions"):
        _probe().build_probe_materialization(
            capture,
            tolerances=LiftingTolerances(1.5, 1e-6, 1e-6, 1e-6),
        )


def test_corridor_changes_preserve_fixed_dp_request_identity(monkeypatch) -> None:
    probe = _probe()
    tolerances = LiftingTolerances(1.5, 1e-6, 1e-6, 1e-6)
    first_capture = _capture()
    second_capture = deepcopy(first_capture)
    second_capture["lifting_corridor"]["route_samples"][0]["s"] = 1.0
    second_capture["lifting_corridor"]["predecessor_receipt"]["s"] = 1.0
    _reseal_corridor(second_capture)

    first_materialized, first_context, _ = probe.build_probe_materialization(
        first_capture, tolerances=tolerances
    )
    second_materialized, second_context, _ = probe.build_probe_materialization(
        second_capture, tolerances=tolerances
    )
    assert first_context.source_sha256 != second_context.source_sha256
    assert first_materialized.metadata["decision_id"] == second_materialized.metadata[
        "decision_id"
    ]
    assert set(first_materialized.dp_input) == set(second_materialized.dp_input)
    for name in first_materialized.dp_input:
        np.testing.assert_array_equal(
            first_materialized.dp_input[name], second_materialized.dp_input[name]
        )

    requests = []
    output = SimpleNamespace(exists=lambda: False)
    monkeypatch.setattr(
        probe,
        "write_request",
        lambda _directory, _causal_input, metadata: requests.append(metadata),
    )
    monkeypatch.setattr(probe, "_write_json_atomic", lambda _path, _value: None)
    for capture in (first_capture, second_capture):
        probe.write_probe_requests(
            capture,
            tolerances=tolerances,
            camp_request_dir=output,
            default_request_dir=output,
            context_path=output,
            camp_head="c" * 40,
            dp_head=FIXED_DP_HEAD,
            selector_hashes=("1" * 64, "2" * 64, "3" * 64),
        )

    top_level_context = probe.build_route_lifting_context(
        route_source=first_capture["route_source"],
        route_samples=first_capture["route_samples"],
        directed_edges=first_capture["directed_edges"],
        route_sample_step_m=first_capture["route_sample_step_m"],
        tolerances=tolerances,
        map_sha256=first_capture["map_sha256"],
    )
    for first, second in zip(requests[:2], requests[2:]):
        assert first["scenario_token"] == top_level_context.source_sha256
        assert first["scenario_token"] == second["scenario_token"]
        assert first["pair_run_key"] == second["pair_run_key"]
        assert first["tick_seed"] == second["tick_seed"]


@pytest.mark.parametrize("mismatched_tokens", (False, True))
def test_lifting_receipt_uses_paired_dp_request_token(
    tmp_path, monkeypatch, mismatched_tokens: bool
) -> None:
    probe, capture, xodr, camp_dir, default_dir, context_path = (
        _write_receipt_inputs(tmp_path)
    )
    _, corridor_context, _ = probe.build_probe_materialization(
        capture, tolerances=probe.FROZEN_LIFTING_TOLERANCES
    )
    top_level_context = probe.build_route_lifting_context(
        route_source=capture["route_source"],
        route_samples=capture["route_samples"],
        directed_edges=capture["directed_edges"],
        route_sample_step_m=capture["route_sample_step_m"],
        tolerances=probe.FROZEN_LIFTING_TOLERANCES,
        map_sha256=capture["map_sha256"],
    )
    camp_path = camp_dir / "request.json"
    default_path = default_dir / "request.json"
    camp_request = json.loads(camp_path.read_text(encoding="utf-8"))
    default_request = json.loads(default_path.read_text(encoding="utf-8"))
    assert camp_request["scenario_token"] == default_request["scenario_token"]
    assert camp_request["scenario_token"] == top_level_context.source_sha256
    assert camp_request["scenario_token"] != corridor_context.source_sha256

    camp_token = camp_request["scenario_token"]
    if mismatched_tokens:
        default_request["scenario_token"] = "not-the-camp-token"
        default_path.write_text(json.dumps(default_request), encoding="utf-8")
    provenances = []
    _stub_receipt_responses(monkeypatch, probe, camp_dir, provenances)

    receipt_path = tmp_path / "receipt.json"
    if mismatched_tokens:
        with pytest.raises(ValueError, match="request scenario tokens mismatch"):
            probe.write_lifting_receipt(
                capture=capture,
                context_path=context_path,
                camp_request_dir=camp_dir,
                default_request_dir=default_dir,
                map_api=SimpleNamespace(to_opendrive=lambda: xodr),
                output_path=receipt_path,
            )
    else:
        probe.write_lifting_receipt(
            capture=capture,
            context_path=context_path,
            camp_request_dir=camp_dir,
            default_request_dir=default_dir,
            map_api=SimpleNamespace(to_opendrive=lambda: xodr),
            output_path=receipt_path,
        )
        assert provenances[0]["scenario_token"] == camp_token
        assert provenances[0]["capture_sha256"] == canonical_json_sha256(capture)
        assert provenances[0]["lifting_corridor_sha256"] == capture[
            "lifting_corridor"
        ]["corridor_sha256"]


@pytest.mark.parametrize("carrier", ("context_sample", "context_edges", "transform"))
def test_lifting_receipt_rejects_serialized_carrier_tampering(
    tmp_path, monkeypatch, carrier: str
) -> None:
    probe, capture, xodr, camp_dir, default_dir, context_path = (
        _write_receipt_inputs(tmp_path)
    )
    payload = json.loads(context_path.read_text(encoding="utf-8"))
    if carrier == "context_sample":
        payload["context"]["samples"][0]["x"] += 1.0
    elif carrier == "context_edges":
        payload["context"]["edges"].append(
            [["1", 0, -1], ["1", 0, -1]]
        )
    else:
        payload["agents_from_world_tf"][0][2] += 1.0
    context_path.write_text(json.dumps(payload), encoding="utf-8")
    _stub_receipt_responses(monkeypatch, probe, camp_dir)

    expected = "serialized lifting transform" if carrier == "transform" else "serialized lifting context"
    with pytest.raises(ValueError, match=expected):
        probe.write_lifting_receipt(
            capture=capture,
            context_path=context_path,
            camp_request_dir=camp_dir,
            default_request_dir=default_dir,
            map_api=SimpleNamespace(to_opendrive=lambda: xodr),
            output_path=tmp_path / "receipt.json",
        )


@pytest.mark.parametrize("request_name", ("camp", "default"))
def test_lifting_receipt_rejects_tampered_fixed_dp_head(
    tmp_path, monkeypatch, request_name: str
) -> None:
    probe, capture, xodr, camp_dir, default_dir, context_path = (
        _write_receipt_inputs(tmp_path)
    )
    request_dir = camp_dir if request_name == "camp" else default_dir
    request_path = request_dir / "request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request["dp_head"] = "d" * 40
    request_path.write_text(json.dumps(request), encoding="utf-8")
    _stub_receipt_responses(monkeypatch, probe, camp_dir)

    with pytest.raises(ValueError, match="fixed DP commit"):
        probe.write_lifting_receipt(
            capture=capture,
            context_path=context_path,
            camp_request_dir=camp_dir,
            default_request_dir=default_dir,
            map_api=SimpleNamespace(to_opendrive=lambda: xodr),
            output_path=tmp_path / "receipt.json",
        )


def test_lifting_receipt_rejects_mixed_capture_request_arrays(
    tmp_path, monkeypatch
) -> None:
    probe, capture, xodr, _, default_dir, context_path = _write_receipt_inputs(
        tmp_path / "trusted"
    )
    other_capture = deepcopy(capture)
    for frame in other_capture["frames"]:
        frame["ego_state"][0] += 1.0
    _, _, _, other_camp_dir, _, _ = _write_receipt_inputs(
        tmp_path / "other", other_capture
    )
    _stub_receipt_responses(monkeypatch, probe, other_camp_dir)

    with pytest.raises(ValueError, match="request arrays do not match rebuilt capture"):
        probe.write_lifting_receipt(
            capture=capture,
            context_path=context_path,
            camp_request_dir=other_camp_dir,
            default_request_dir=default_dir,
            map_api=SimpleNamespace(to_opendrive=lambda: xodr),
            output_path=tmp_path / "receipt.json",
        )


def test_lifting_receipt_rejects_responses_from_other_same_route_request(
    tmp_path, monkeypatch
) -> None:
    probe, capture, xodr, camp_dir, default_dir, context_path = (
        _write_receipt_inputs(tmp_path / "trusted")
    )
    other_capture = deepcopy(capture)
    other_capture["decision_timestamp_us"] += 100_000
    for frame in other_capture["frames"]:
        frame["timestamp_us"] += 100_000
        frame["ego_state"][0] += 1.0
    _, _, _, other_camp_dir, other_default_dir, _ = _write_receipt_inputs(
        tmp_path / "other", other_capture
    )
    bridge = importlib.import_module(
        "camp_core.integrations.diffusion_planner_v19_nuplan_bridge"
    )
    other_camp_request = json.loads(
        (other_camp_dir / "request.json").read_text(encoding="utf-8")
    )
    other_default_request = json.loads(
        (other_default_dir / "request.json").read_text(encoding="utf-8")
    )
    trusted_camp_request = json.loads(
        (camp_dir / "request.json").read_text(encoding="utf-8")
    )
    assert other_camp_request["run_key"] == trusted_camp_request["run_key"]
    assert (
        other_camp_request["causal_input_sha256"]
        != trusted_camp_request["causal_input_sha256"]
    )
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    trajectory = np.zeros((80, 4), dtype=np.float32)
    bridge.write_response(
        other_camp_dir,
        {
            "candidates": candidates,
            "route_speed_source_eligible_mask": np.zeros(8, dtype=bool),
        },
        {
            "schema_version": bridge.BRIDGE_SCHEMA_VERSION,
            "arm": "camp",
            "run_key": other_camp_request["run_key"],
            "iteration_index": 0,
            "operation": "source_probe",
            "speed_source_policy": "candidate_local_exact_speed",
            "status": "ok",
            "native_ranked_top1": False,
            "candidate_sha256_before": bridge.array_sha256(candidates),
            "candidate_sha256_after": bridge.array_sha256(candidates),
            "dp_default_source_complete": False,
            "eligible_candidate_count": 0,
            "request_evidence": _request_evidence(other_camp_request),
        },
    )
    bridge.write_response(
        other_default_dir,
        {"selected_trajectory": trajectory},
        {
            "schema_version": bridge.BRIDGE_SCHEMA_VERSION,
            "arm": "dp_default",
            "run_key": other_default_request["run_key"],
            "iteration_index": 0,
            "operation": "plan_tick",
            "speed_source_policy": "candidate_local_exact_speed",
            "status": "ok",
            "native_ranked_top1": False,
            "baseline_name": bridge.DP_OPERATIONAL_TOP1_NAME,
            "baseline_provenance": bridge.DP_OPERATIONAL_TOP1_PROVENANCE,
            "selected_trajectory_sha256": bridge.array_sha256(trajectory),
            "selected_planned_red_light_cost": 0.0,
            "planned_red_source": "fixed_dp_red_cost_v18",
            "worker_latency_ms": {"dp_inference": 1.0, "atom_selector": 0.0},
            "request_evidence": _request_evidence(other_default_request),
        },
    )
    for source, target in (
        (other_camp_dir, camp_dir),
        (other_default_dir, default_dir),
    ):
        for name in ("response.npz", "response.json"):
            shutil.copyfile(source / name, target / name)
    monkeypatch.setattr(probe, "lift_k8_route_receipt", lambda **_kwargs: {})

    with pytest.raises(ValueError, match="request evidence"):
        probe.write_lifting_receipt(
            capture=capture,
            context_path=context_path,
            camp_request_dir=camp_dir,
            default_request_dir=default_dir,
            map_api=SimpleNamespace(to_opendrive=lambda: xodr),
            output_path=tmp_path / "receipt.json",
        )


def test_lifting_receipt_rejects_self_consistent_metadata_from_other_log(
    tmp_path, monkeypatch
) -> None:
    probe, capture, xodr, camp_dir, default_dir, context_path = (
        _write_receipt_inputs(tmp_path)
    )
    materialized, _, _ = probe.build_probe_materialization(
        capture, tolerances=probe.FROZEN_LIFTING_TOLERANCES
    )
    camp_path = camp_dir / "request.json"
    default_path = default_dir / "request.json"
    original_camp = json.loads(camp_path.read_text(encoding="utf-8"))
    common = {
        "log_name": "OtherTown",
        "scenario_token": original_camp["scenario_token"],
        "iteration_index": 0,
        "simulation_time_us": capture["decision_timestamp_us"],
        "scenario_seed": 3411,
        "dp_seed_root": 3412,
        "camp_head": "c" * 40,
        "dp_head": FIXED_DP_HEAD,
        "nuplan_head": capture["source_head"],
        "causal_input": materialized.dp_input,
        "speed_source_policy": "candidate_local_exact_speed",
    }
    changed_camp = probe.build_request_metadata(
        arm="camp",
        selector_hashes=("1" * 64, "2" * 64, "3" * 64),
        **common,
    )
    changed_default = probe.build_request_metadata(arm="dp_default", **common)
    for field in ("pair_run_key", "run_key", "tick_seed"):
        assert changed_camp[field] != original_camp[field]
    camp_path.write_text(json.dumps(changed_camp), encoding="utf-8")
    default_path.write_text(json.dumps(changed_default), encoding="utf-8")
    _stub_receipt_responses(monkeypatch, probe, camp_dir)

    with pytest.raises(ValueError, match="run key mismatch|request metadata"):
        probe.write_lifting_receipt(
            capture=capture,
            context_path=context_path,
            camp_request_dir=camp_dir,
            default_request_dir=default_dir,
            map_api=SimpleNamespace(to_opendrive=lambda: xodr),
            output_path=tmp_path / "receipt.json",
        )


@pytest.mark.parametrize(
    ("tamper", "match"),
    (("camp_head", "CAMP heads"), ("selector_hash", "selector SHA256")),
)
def test_lifting_receipt_validates_unsealed_request_parameters(
    tmp_path, monkeypatch, tamper: str, match: str
) -> None:
    probe, capture, xodr, camp_dir, default_dir, context_path = (
        _write_receipt_inputs(tmp_path)
    )
    request_dir = default_dir if tamper == "camp_head" else camp_dir
    request_path = request_dir / "request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    if tamper == "camp_head":
        request["camp_head"] = "d" * 40
    else:
        request["selector_hashes"][0] = "bad"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    _stub_receipt_responses(monkeypatch, probe, camp_dir)

    with pytest.raises(ValueError, match=match):
        probe.write_lifting_receipt(
            capture=capture,
            context_path=context_path,
            camp_request_dir=camp_dir,
            default_request_dir=default_dir,
            map_api=SimpleNamespace(to_opendrive=lambda: xodr),
            output_path=tmp_path / "receipt.json",
        )


def test_build_probe_materialization_reuses_causal_and_lifting_contracts() -> None:
    materialized, context, transform = _probe().build_probe_materialization(
        _capture(),
        tolerances=LiftingTolerances(
            1.5273609989704584,
            1.0000017763568395e-9,
            1e-9,
            1.0000017763568395e-9,
        ),
    )

    assert set(materialized.dp_input) == set(CAUSAL_DP_INPUT_SCHEMA)
    assert not materialized.dp_input["route_lanes_has_speed_limit"].any()
    assert context.edges == ((("1", 0, -1), ("2", 0, -1)),)
    assert len(context.source_sha256) == 64
    np.testing.assert_array_equal(transform, np.eye(3))


def test_frozen_station_tolerance_covers_carla_float32_xodr_api() -> None:
    probe = _probe()
    bound = 3.0517578125e-05
    allowance = 1e-9

    assert probe.FROZEN_LIFTING_TOLERANCES == LiftingTolerances(
        1.5273609989704584,
        bound + allowance,
        1e-9,
        bound + allowance,
    )
    road_length = 966.8900000000001
    assert abs(float(np.float32(road_length)) - road_length) <= bound


def test_build_probe_materialization_rejects_outcomes() -> None:
    capture = _capture()
    capture["safety_outcome"] = 0.0

    with pytest.raises(ValueError, match="forbidden source field"):
        _probe().build_probe_materialization(
            capture,
            tolerances=LiftingTolerances(1.5, 1e-9, 1e-9, 1e-9),
        )


def test_write_probe_requests_is_exactly_once() -> None:
    output = SimpleNamespace(exists=lambda: True)

    with pytest.raises(FileExistsError, match="already exists"):
        _probe().write_probe_requests(
            _capture(),
            tolerances=LiftingTolerances(1.5, 1e-9, 1e-9, 1e-9),
            camp_request_dir=output,
            default_request_dir=output,
            context_path=output,
            camp_head="c" * 40,
            dp_head=FIXED_DP_HEAD,
            selector_hashes=("1" * 64, "2" * 64, "3" * 64),
        )


def test_write_probe_requests_rejects_content_digest_as_git_head() -> None:
    output = SimpleNamespace(exists=lambda: False)

    with pytest.raises(ValueError, match="CAMP head Git commit is invalid"):
        _probe().write_probe_requests(
            _capture(),
            tolerances=LiftingTolerances(1.5, 1e-9, 1e-9, 1e-9),
            camp_request_dir=output,
            default_request_dir=output,
            context_path=output,
            camp_head="c" * 64,
            dp_head=FIXED_DP_HEAD,
            selector_hashes=("1" * 64, "2" * 64, "3" * 64),
        )


def test_write_probe_requests_rejects_nonfixed_dp_head(monkeypatch) -> None:
    probe = _probe()
    output = SimpleNamespace(exists=lambda: False)
    monkeypatch.setattr(probe, "write_request", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(probe, "_write_json_atomic", lambda *_args, **_kwargs: None)

    with pytest.raises(ValueError, match="fixed DP commit"):
        probe.write_probe_requests(
            _capture(),
            tolerances=probe.FROZEN_LIFTING_TOLERANCES,
            camp_request_dir=output,
            default_request_dir=output,
            context_path=output,
            camp_head="c" * 40,
            dp_head="d" * 40,
            selector_hashes=("1" * 64, "2" * 64, "3" * 64),
        )


def test_write_probe_requests_freezes_source_only_metadata(monkeypatch) -> None:
    probe = _probe()
    output = SimpleNamespace(exists=lambda: False)
    requests = []
    monkeypatch.setattr(
        probe,
        "write_request",
        lambda directory, causal_input, metadata: requests.append(metadata),
    )
    monkeypatch.setattr(probe, "_write_json_atomic", lambda path, value: None)

    probe.write_probe_requests(
        _capture(),
        tolerances=LiftingTolerances(1.5, 1e-9, 1e-9, 1e-9),
        camp_request_dir=output,
        default_request_dir=output,
        context_path=output,
        camp_head="c" * 40,
        dp_head=FIXED_DP_HEAD,
        selector_hashes=("1" * 64, "2" * 64, "3" * 64),
    )

    assert [request["arm"] for request in requests] == ["camp", "dp_default"]
    assert all(request["scenario_seed"] == 3411 for request in requests)
    assert all(request["dp_seed_root"] == 3412 for request in requests)
    assert all(
        request["speed_source_policy"] == "candidate_local_exact_speed"
        for request in requests
    )
    assert requests[0]["selector_hashes"] == ["1" * 64, "2" * 64, "3" * 64]
    assert "selector_hashes" not in requests[1]
    assert all("selected_index" not in request for request in requests)
    assert all("outcome" not in " ".join(request).lower() for request in requests)
    assert all(request["camp_head"] == "c" * 40 for request in requests)
    assert all(request["dp_head"] == FIXED_DP_HEAD for request in requests)
