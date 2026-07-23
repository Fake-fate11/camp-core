from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (
    capacity_decision,
    fresh_power_at_corridor_ceiling,
)
from camp_core.integrations.diffusion_planner_v25_fresh_storage import (
    analyze_storage_tree,
)


ROOT = Path(__file__).resolve().parents[2]


def _module(relative: str, name: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PRODUCER = _module(
    "scripts/integrations/freeze_diffusion_planner_v25_fresh_b2_preopen.py",
    "v25_fresh_b2_preopen_producer",
)


def _power_source() -> dict:
    metric = lambda sigma: {"cluster_standard_deviation": sigma}  # noqa: E731
    return {
        "fresh_b2_power_sensitivity": {
            "camp_static14d_minus_candidate0": {
                "safety_cost_total": metric(2.0),
                "red_light_component": metric(0.2),
            },
            "camp_scene14d_no_v2i_minus_candidate0": {
                "safety_cost_total": metric(3.0),
                "red_light_component": metric(0.3),
            },
        }
    }


def _storage_source(tmp_path: Path) -> Path:
    root = tmp_path / "calibration"
    for index, arm in enumerate(("candidate0", "static14d", "scene14d")):
        run = root / "runs" / f"{index:04d}_{arm}"
        run.mkdir(parents=True)
        (run / "decision_evidence.json").write_bytes(
            (json.dumps({"arm": arm, "payload": "x" * 2000}, sort_keys=True, separators=(",", ":")) + "\n").encode()
        )
        (run / "terminal.json").write_text("{}\n", encoding="utf-8")
    return root


def test_power_recomputes_at_real_100_corridor_ceiling() -> None:
    result = fresh_power_at_corridor_ceiling(_power_source(), corridor_count=100)
    assert result["independent_corridor_ceiling"] == 100
    assert result["seed_count"] == 5
    assert result["seeds_or_ticks_counted_as_independent"] is False
    assert (
        result["comparisons"]["camp_static14d_minus_candidate0"]["safety_cost_total"][
            "independent_cluster_count"
        ]
        == 100
    )
    with pytest.raises(ValueError, match="100-corridor"):
        fresh_power_at_corridor_ceiling(_power_source(), corridor_count=500)


def test_capacity_preserves_floor_and_reserve_from_bit_exact_measurement(
    tmp_path: Path,
) -> None:
    source = _storage_source(tmp_path)
    manifest = analyze_storage_tree(source, work_root=tmp_path / "storage", minimum_free_bytes=0)
    projected = manifest["metrics"]["projected_1500_arm_upper_bound_nbytes"]
    result = capacity_decision(
        manifest,
        free_bytes_before=projected + 12 * 1024**3,
        output_parent=tmp_path,
        storage_review_status="passed_independent_fresh_storage_equivalence_and_capacity_review",
    )
    assert result["status"] == "passed_fresh_b2_storage_capacity"
    assert result["reserve_beyond_10gib_floor_bytes"] == 2 * 1024**3
    with pytest.raises(ValueError, match="floor/reserve"):
        capacity_decision(
            manifest,
            free_bytes_before=projected + 10 * 1024**3,
            output_parent=tmp_path,
            storage_review_status="passed_independent_fresh_storage_equivalence_and_capacity_review",
        )


def test_preopen_config_is_unopened_and_rejects_nonce_mutation() -> None:
    path = ROOT / "configs/integrations/diffusion_planner_v25_fresh_b2_preopen_authority_v1.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert path.read_bytes() == (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    assert PRODUCER._validate_config(value)["one_time_state"]["nonce_created"] is False
    assert (
        value["upstream_artifacts"]["corrected_corpus"]["root_sha256"]
        == "97a361b2bbb3544e842c9b6d12b3c17b8f63982db3217e9e360643b0cd7b0ffd"
    )
    assert (
        value["upstream_artifacts"]["corrected_corpus_review"]["root_sha256"]
        == "548a5468e585bd39bfbb58ecfd4780e6c78ff88cddb7fef985532639d8dd2c4a"
    )
    mutated = copy.deepcopy(value)
    mutated["one_time_state"]["nonce_created"] = True
    with pytest.raises(ValueError, match="closed-state"):
        PRODUCER._validate_config(mutated)
