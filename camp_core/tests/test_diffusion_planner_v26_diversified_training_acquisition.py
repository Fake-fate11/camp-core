from __future__ import annotations

import importlib
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np

from camp_core.integrations.diffusion_planner_v25_context import RAW_FEATURE_NAMES
from camp_core.integrations.diffusion_planner_v26_development_profiling import (
    OPERATIONAL_ARM,
    PROFILE_ARMS,
)
from camp_core.integrations.diffusion_planner_v26_integration_boundary import (
    V26CertifiedNoSignalAbsenceAdapter,
)
from camp_core.integrations.diffusion_planner_v26_scene14d_adapter import (
    V26FrozenScene14DAdapter,
    build_v26_scene14d_context,
)
from camp_core.integrations.diffusion_planner_v26_source_authority import (
    V26_SOURCE_TRAFFIC_SIGNAL_MODE,
    v26_source_projection_binding,
)


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _sha(index: int) -> str:
    return f"{index:064x}"


def _schedule(*, map_path: str = "/root/autodl-tmp/maps/simple.osm", map_sha256: str | None = None) -> dict[str, object]:
    return {
        "family_id": "legacy_simple_cross",
        "route_id": "legacy_simple_cross/route-0000",
        "corridor_id": _sha(9),
        "source_artifact_sha256": _sha(10),
        "event_manifest_sha256": _sha(11),
        "route_record": {
            "identity_sha256": _sha(12),
            "source_map_path": map_path,
            "source_map_sha256": _sha(13) if map_sha256 is None else map_sha256,
            "source_geometry_sha256": _sha(14),
            "lanelet_ids": [1, 2],
            "source_stratum": {
                "traffic_light": False,
                "branch_intersection": False,
                "tight_corridor": True,
                "short_progress_opportunity": False,
            },
            "route_spec": {
                "map_path": map_path,
                "lanelet_ids": [1, 2],
                "start_pose": [0.0, 0.0, 0.0],
                "goal_pose": [1.0, 0.0, 0.0],
                "route_length_m": 20.0,
            },
        },
    }


def _write_source_map(path: Path, *, traffic: bool) -> str:
    regulatory = "" if not traffic else """
  <relation id=\"100\">
    <member type=\"way\" ref=\"10\" role=\"refers\"/>
    <member type=\"way\" ref=\"11\" role=\"ref_line\"/>
    <member type=\"way\" ref=\"12\" role=\"light_bulbs\"/>
    <tag k=\"type\" v=\"regulatory_element\"/>
    <tag k=\"subtype\" v=\"traffic_light\"/>
  </relation>"""
    lanelet_reg = "" if not traffic else '<member type="relation" ref="100" role="regulatory_element"/>'
    path.write_text(
        f"""<osm version=\"0.6\">
  <node id=\"1\" lat=\"0.665608\" lon=\"-0.559376\"/>
  <node id=\"2\" lat=\"0.665609\" lon=\"-0.559375\"/>
  <node id=\"3\" lat=\"0.665610\" lon=\"-0.559374\"/>
  <way id=\"10\"><nd ref=\"1\"/><nd ref=\"2\"/></way>
  <way id=\"11\"><nd ref=\"1\"/><nd ref=\"2\"/></way>
  <way id=\"12\"><nd ref=\"2\"/><nd ref=\"3\"/></way>
  <relation id=\"1\">
    {lanelet_reg}
    <tag k=\"type\" v=\"lanelet\"/>
  </relation>{regulatory}
</osm>""",
        encoding="utf-8",
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _raw() -> dict[str, object]:
    rows = [_sha(100 + index) for index in range(8)]
    atom_source = np.ones((8, 14), dtype=bool).tolist()
    arms = {}
    for arm_id in PROFILE_ARMS:
        selected = 0 if arm_id == OPERATIONAL_ARM else 1
        arms[arm_id] = {
            "status": "ok",
            "failure_reason": None,
            "selected_index": selected,
            "selected_row_sha256": rows[selected],
            "source_valid_mask": [True] * 8,
            "physical_feasible_mask": [True] * 8,
            "margin_best_vs_runner_up": None if arm_id == OPERATIONAL_ARM else 1.0,
            "exact_tie_set": [selected],
        }
    return {
        "status": "ok",
        "candidate_row_sha256": rows,
        "candidate_tensor_sha256_before": _sha(200),
        "candidate_tensor_sha256_after": _sha(200),
        "zero_call_receipt": {
            "dp_or_model_calls_after_pool": 0,
            "latent_replacements_after_pool": 0,
            "candidate_generations_after_pool": 0,
        },
        "primary_pool_model_call_count": 1,
        "same_ego_batch_metadata": {
            "same_ego_batch_size": 8,
            "nonlatent_rows_identical": True,
            "tensor_metadata": {"history": {"shape": [8, 3], "dtype": "torch.float32", "finite": True}},
        },
        "selected_index": 0,
        "selected_trajectory_sha256": rows[0],
        "state_sha256": _sha(201),
        "source_input_sha256": _sha(202),
        "input_sha256": _sha(203),
        "latent_seed": 24001,
        "latent_shape": [8, 321, 81, 4],
        "latent_dtype": "float32",
        "latent_tensor_sha256": _sha(204),
        "latent_row_sha256": [_sha(210 + index) for index in range(8)],
        "candidate_shape": [8, 80, 4],
        "candidate_dtype": "float32",
        "candidate_finite": True,
        "default_output_sha256": rows[0],
        "real_selector_receipts": arms,
        "integration_boundary": {"runner_id": "fixture"},
        "controlled_scene": {"status": "fixture"},
        "causal_signal_atom_input_sha256": _sha(205),
        "materialized_summary": {
            "atom_matrix": np.ones((8, 14), dtype=np.float64).tolist(),
            "atom_matrix_sha256": _sha(206),
            "atom_source_valid_mask": atom_source,
            "atom_applicable_mask": atom_source,
            "source_valid_mask": [True] * 8,
            "physical_feasible_mask": [True] * 8,
            "context": {
                "raw_context": {name: float(index) for index, name in enumerate(RAW_FEATURE_NAMES)},
                "source_complete": {name: True for name in RAW_FEATURE_NAMES},
            },
            "atom_materialization_phase_receipt": {"projection": {"status": "measured"}},
        },
    }


def test_completed_unit_retains_b8_masks_hashes_and_candidate0() -> None:
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_diversified_training_acquisition"
    )
    unit = runner._completed_unit(
        _raw(),
        SimpleNamespace(model_call_count=1),
        unit_index=0,
        route_plan_sha256=_sha(1),
        schedule=_schedule(),
        scenario_seed=46001,
    )

    assert unit["forward_calls"]["primary_forward_count"] == 1
    assert unit["forward_calls"]["sequential_forward_count"] == 0
    assert unit["candidate_pool"]["candidate0"]["index"] == 0
    assert unit["action"]["simulator_selected_row_sha256"] == unit["candidate_pool"]["row_sha256"][0]
    assert np.asarray(unit["training_pool"]["atom_source_valid_mask"]).shape == (8, 14)


def test_source_signal_authority_accepts_real_traffic_and_certifies_only_actual_absence(
    tmp_path: Path,
) -> None:
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_diversified_training_acquisition"
    )
    traffic_map = tmp_path / "traffic.osm"
    traffic_sha = _write_source_map(traffic_map, traffic=True)
    traffic = _schedule(map_path=str(traffic_map), map_sha256=traffic_sha)
    traffic["route_record"]["source_stratum"] = {
        **traffic["route_record"]["source_stratum"],
        "traffic_light": True,
    }
    configuration, failure = runner._signal_config(
        schedule=traffic, family={"sidecar": None}, route_sha256=_sha(2)
    )
    assert failure is None
    assert configuration["signal_authority_mode"] == V26_SOURCE_TRAFFIC_SIGNAL_MODE
    assert configuration["source_map_traffic_authority"]["traffic_light_regulatory_element_ids"] == [100]

    no_signal_map = tmp_path / "no_signal.osm"
    no_signal_sha = _write_source_map(no_signal_map, traffic=False)
    schedule = _schedule(map_path=str(no_signal_map), map_sha256=no_signal_sha)
    configuration, failure = runner._signal_config(
        schedule=schedule, family={"sidecar": None}, route_sha256=_sha(2)
    )
    assert failure is None
    assert configuration["signal_authority_mode"] == "certified_no_signal"
    assert configuration["certified_no_signal_authority"]["traffic_light_regulatory_element_ids"] == []

    false_absence = _schedule(map_path=str(traffic_map), map_sha256=traffic_sha)
    configuration, failure = runner._signal_config(
        schedule=false_absence, family={"sidecar": None}, route_sha256=_sha(2)
    )
    assert configuration is None
    assert "conflicts with source traffic authority" in failure


def test_source_projection_and_no_signal_causal_hash_use_the_frozen_schema(tmp_path: Path) -> None:
    source = tmp_path / "simple.osm"
    source_sha = _write_source_map(source, traffic=False)
    projection = v26_source_projection_binding(source, source_sha)
    assert projection["utm_zone"] == 30
    assert projection["source_map_sha256"] == source_sha

    authority = {
        "schema_version": "camp_dp_v26_certified_no_signal_authority_v1",
        "route_sha256": _sha(1),
        "map_sha256": _sha(2),
        "route_lanelet_ids": [1],
        "route_geometry_sha256": _sha(3),
        "source_chain_sha256": _sha(4),
        "certification_sha256": _sha(5),
        "traffic_light_regulatory_element_ids": [],
    }

    class _Lanelet:
        def trafficLights(self):
            return []

    adapter = V26CertifiedNoSignalAbsenceAdapter(authority)
    adapter.bind_builder(SimpleNamespace(_ll_by_id={1: _Lanelet()}))
    adapter.bind_runtime_lanelet_ids(route_lanelet_ids=[1], map_lanelet_ids=[1])
    payload = adapter.causal_signal_atom_input(SimpleNamespace(dt=0.1), 0)
    assert payload["source_state"] == "not_applicable"


def test_v26_scene14d_adapter_requires_exact_complete_finite_reference_payload() -> None:
    class _Scaler:
        q05 = np.zeros(26, dtype=np.float64)
        q95 = np.ones(26, dtype=np.float64)

    class _Provider:
        theta = np.full((14, 53), 1.0 / 14.0, dtype=np.float64)
        context_scaler = _Scaler()
        context_scaler_sha256 = _sha(6)
        theta_sha256 = _sha(7)

        def __call__(self, payload):
            assert payload["schema_version"] == "camp_dp_v25_causal_context_raw_v2"
            return {
                "weights": [1.0 / 14.0] * 14,
                "context_scaler_sha256": self.context_scaler_sha256,
                "theta_sha256": self.theta_sha256,
                "runtime_projection": False,
                "softmax": False,
            }

    raw = {name: float(index) for index, name in enumerate(RAW_FEATURE_NAMES)}
    complete = {name: True for name in RAW_FEATURE_NAMES}
    payload = build_v26_scene14d_context(
        raw_context=raw,
        source_complete=complete,
        source_receipt={
            "mode": "no_v2i",
            "phase_remaining_available": False,
            "regulatory_signal_mapped": False,
        },
    )
    adapter = V26FrozenScene14DAdapter(_Provider())
    assert adapter(payload)["runtime_projection"] is False


def test_parser_and_source_keep_the_v26_native_boundary() -> None:
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_diversified_training_acquisition"
    )
    args = runner.parse_args(
        [
            "--output-dir", "out",
            "--worker-lock", "lock",
            "--route-plan", "plan.json",
            "--base-probe-config", "base.json",
            "--reference-weights", "weights",
            "--reference-weights-root", _sha(3),
            "--reference-weights-review", "review",
            "--reference-weights-review-root", _sha(4),
            "--fixed-dp-repo", "fixed-dp",
            "--expected-camp-head", "a" * 40,
            "--pre-model-qualification", "qualification.json",
        ]
    )
    assert args.device == "cuda"
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert "run_v26_native_same_ego_b8_replay" in source
    assert "validate_diffusion_planner_v25_fair_nonholdout" not in source
    assert "run_diffusion_planner_v25_industrial_bounded_closed_loop" not in source
    assert "_build_no_signal_chain" not in source


def test_revised_plan_preserves_parent_ordinal_for_seed_and_receipt() -> None:
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_diversified_training_acquisition"
    )
    schedule = _schedule()
    schedule["parent_ordinal"] = 1187
    assert runner._source_ordinal(schedule, 1185) == 1187
    unit = runner._typed_failure_unit(
        unit_index=1185,
        route_plan_sha256=_sha(1),
        schedule=schedule,
        scenario_seed=46001 + 1187,
        failure_class="fixture",
        failure_reason="fixture",
    )
    assert unit["route"]["parent_ordinal"] == 1187


def test_training_scales_receipt_is_converted_to_json_native_values() -> None:
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_diversified_training_acquisition"
    )
    receipt = {
        "scales": np.asarray([1.0, 2.0], dtype=np.float64),
        "count": np.int64(2),
        "nested": {"mask": np.asarray([True, False], dtype=np.bool_)},
    }
    native = runner._json_native(receipt)
    assert json.loads(json.dumps(native)) == {
        "scales": [1.0, 2.0],
        "count": 2,
        "nested": {"mask": [True, False]},
    }


def test_atomic_training_artifact_writer_serializes_numpy_scale_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_diversified_training_acquisition"
    )
    unit = runner._completed_unit(
        _raw(),
        SimpleNamespace(model_call_count=1),
        unit_index=0,
        route_plan_sha256=_sha(1),
        schedule=_schedule(),
        scenario_seed=46001,
    )
    monkeypatch.setattr(
        runner,
        "fit_train_only_atom_scales",
        lambda *args, **kwargs: {
            "scales": np.ones(14, dtype=np.float64),
            "diagnostic": np.asarray([1, 2], dtype=np.int64),
        },
    )
    runner._AcquisitionLedger.write_training_artifacts_from_atomic_units(
        output_dir=tmp_path,
        manifest={"route_plan_sha256": _sha(1)},
        complete=[unit],
    )
    payload = json.loads((tmp_path / "training_scales.json").read_text(encoding="utf-8"))
    assert payload["scales"] == [1.0] * 14
    assert payload["diagnostic"] == [1, 2]
