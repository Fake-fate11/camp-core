from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from types import SimpleNamespace
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations import diffusion_planner_v26_nuplan as nuplan  # noqa: E402


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _record(
    index: int,
    *,
    split: str,
    city: str = "boston",
    family: str = "us-ma-boston",
    corridor: str | None = None,
) -> dict[str, object]:
    return {
        "record_id": f"record-{index:03d}",
        "official_split": split,
        "log_token": f"log-{index:03d}",
        "scenario_token": f"scenario-{index:03d}",
        "scene_token": f"scene-{index:03d}",
        "state_token": f"state-{index:03d}",
        "mission_route_roadblock_chain_sha256": _sha(f"route-{index}"),
        "corridor_id": corridor or f"corridor-{index:03d}",
        "geometry_clone_group_sha256": _sha(f"geometry-{index}"),
        "city": city,
        "map_family": family,
        "source_db_sha256": _sha(f"db-{index}"),
        "map_sha256": _sha(f"map-{family}"),
        "event_strata": ["intersection"] if index % 2 else ["traffic_light"],
    }


def _raw_source() -> dict[str, str]:
    return {
        "nuplan_dataset_version": "v1.1",
        "official_split_entrypoint": "official_log_split_metadata.json",
        "official_split_metadata_sha256": _sha("official-split"),
        "data_root_identity_sha256": _sha("data-root"),
        "maps_root_identity_sha256": _sha("maps-root"),
    }


def _fixed_dp() -> dict[str, str]:
    return {
        "head": nuplan.FIXED_DP_HEAD,
        "checkpoint_sha256": _sha("checkpoint"),
        "args_sha256": _sha("args"),
    }


def test_identity_only_manifest_keeps_official_groups_disjoint_and_ood_separate() -> None:
    records = [
        _record(1, split="train"),
        _record(2, split="val", city="singapore", family="sg-one-north"),
        _record(3, split="test", city="pittsburgh", family="us-pa-pittsburgh-hazelwood"),
    ]
    manifest = nuplan.build_v26_nuplan_split_manifest(
        records,
        raw_source=_raw_source(),
        fixed_dp=_fixed_dp(),
        camp_source_head="a" * 40,
        ood_city_map_families=[("pittsburgh", "us-pa-pittsburgh-hazelwood")],
    )
    assert manifest["partitions"]["train_iid"]["record_count"] == 1
    assert manifest["partitions"]["val_iid"]["record_count"] == 1
    assert manifest["partitions"]["test_ood"]["record_count"] == 1
    assert manifest["partitions"]["test_iid"]["record_count"] == 0
    assert nuplan.validate_v26_nuplan_split_manifest(manifest) == manifest


def test_manifest_rejects_group_overlap_and_outcome_fields() -> None:
    first = _record(1, split="train", corridor="shared-corridor")
    second = _record(2, split="val", corridor="shared-corridor")
    with pytest.raises(ValueError, match="corridor_id"):
        nuplan.build_v26_nuplan_split_manifest(
            [first, second],
            raw_source=_raw_source(),
            fixed_dp=_fixed_dp(),
            camp_source_head="a" * 40,
        )
    outcome = copy.deepcopy(first)
    outcome["selected_index"] = 0
    with pytest.raises(ValueError, match="outcome field"):
        nuplan.validate_v26_nuplan_source_record(outcome)


def test_same_ego_b8_single_forward_candidate0_and_postpool_zero() -> None:
    class FakeModel:
        def __init__(self) -> None:
            self.calls = 0

        def __call__(self, value):
            self.calls += 1
            assert value["ego"].shape == (8, 2)
            assert value["sampled_trajectories"].shape == (8, 321, 81, 4)
            prediction = np.zeros((8, 321, 80, 4), dtype=np.float32)
            for index in range(8):
                prediction[index, 0, :, 0] = index + 1
            return {"prediction": prediction}

    model = FakeModel()
    pool = nuplan.run_v26_nuplan_single_invocation_b8(
        model=model,
        normalized_single_input={
            "ego": np.array([[1.0, 2.0]], dtype=np.float32),
            "sampled_trajectories": np.zeros((1, 321, 81, 4), dtype=np.float32),
        },
        route_identity_sha256=_sha("route"),
        tick_index=0,
        root_seed=17,
    )
    assert model.calls == 1
    assert pool["primary_forward_count"] == 1
    assert pool["sequential_forward_count"] == 0
    rows = pool["candidate_row_sha256"]
    bound = nuplan.bind_v26_nuplan_same_pool_selectors(
        pool,
        {
            "candidate0": {"selected_index": 0, "selected_row_sha256": rows[0]},
            "Static14D": {"selected_index": 3, "selected_row_sha256": rows[3]},
            "Scene14D": {"selected_index": 5, "selected_row_sha256": rows[5]},
        },
    )
    assert bound["candidate_pool_sha256_before"] == bound["candidate_pool_sha256_after"]
    assert all(value == 0 for value in bound["post_pool_call_counts"].values())


def test_same_pool_binding_rejects_row_or_pool_drift() -> None:
    candidates = np.zeros((8, 80, 4), dtype=np.float32)
    for index in range(8):
        candidates[index, :, 0] = index
    pool = {
        "candidate_tensor": candidates,
        "candidate_tensor_sha256_before": nuplan.array_sha256(candidates),
        "candidate_row_sha256": [nuplan.array_sha256(row) for row in candidates],
    }
    with pytest.raises(ValueError, match="does not bind"):
        nuplan.bind_v26_nuplan_same_pool_selectors(
            pool,
            {
                "candidate0": {"selected_index": 0, "selected_row_sha256": pool["candidate_row_sha256"][0]},
                "Static14D": {"selected_index": 1, "selected_row_sha256": pool["candidate_row_sha256"][2]},
                "Scene14D": {"selected_index": 2, "selected_row_sha256": pool["candidate_row_sha256"][2]},
            },
        )


def test_official_adapter_keeps_missing_speed_as_endpoint_applicability(monkeypatch) -> None:
    source = _record(1, split="train")
    captured = {}

    def materialize(current, initialization, *, speed_source_policy):
        captured["policy"] = speed_source_policy
        return SimpleNamespace(
            dp_input={"lanes_has_speed_limit": np.zeros((2, 1), dtype=bool)},
            metadata={"source": "official"},
        )

    monkeypatch.setattr(nuplan, "materialize_nuplan_planner_input", materialize)
    result = nuplan.materialize_v26_nuplan_planner_input(
        SimpleNamespace(traffic_light_data=[]),
        object(),
        source_identity=source,
    )
    assert captured["policy"] == "candidate_local_exact_speed"
    assert result["endpoint_applicability"] == {
        "red_light": "missing_or_inapplicable",
        "speed_limit": "missing_or_inapplicable",
    }
    assert result["outcome_fields_consumed"] == []


def test_manifest_cli_binds_identity_only_inputs_without_legacy_k8_imports(tmp_path: Path) -> None:
    inventory_path = tmp_path / "inventory.json"
    binding_path = tmp_path / "fixed_dp.json"
    inventory_path.write_text(
        json.dumps(
            {
                "raw_source": _raw_source(),
                "records": [
                    _record(1, split="train"),
                    _record(2, split="val", city="singapore", family="sg-one-north"),
                    _record(3, split="test", city="pittsburgh", family="us-pa-pittsburgh-hazelwood"),
                ],
            }
        ),
        encoding="utf-8",
    )
    binding_path.write_text(json.dumps(_fixed_dp()), encoding="utf-8")
    script_path = ROOT / "scripts/integrations/prepare_diffusion_planner_v26_nuplan_source_manifest.py"
    spec = importlib.util.spec_from_file_location("v26_nuplan_manifest", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    args = module.parse_args(
        [
            "--inventory",
            str(inventory_path),
            "--fixed-dp-binding",
            str(binding_path),
            "--camp-source-head",
            "a" * 40,
            "--ood-city-map-family",
            "pittsburgh:us-pa-pittsburgh-hazelwood",
            "--output",
            str(tmp_path / "manifest.json"),
        ]
    )
    manifest = module.build_manifest(args)
    assert manifest["input_bindings"]["identity_inventory_sha256"] == _sha(
        inventory_path.read_text(encoding="utf-8")
    )
    assert manifest["partitions"]["test_ood"]["record_count"] == 1
    source = (ROOT / "camp_core/camp_core/integrations/diffusion_planner_v26_nuplan.py").read_text(
        encoding="utf-8"
    )
    assert "run_diffusion_planner_dp_camp_v18" not in source
    assert "diffusion_planner_v25" not in source
