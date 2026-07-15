from __future__ import annotations

import inspect
import importlib.machinery
import json
import types
from pathlib import Path

from scripts.integrations.prepare_diffusion_planner_v24_single_record_probe import (
    PROBE_SEED,
    build_probe_config,
    select_probe_route,
)
from scripts.integrations import run_diffusion_planner_dp_camp_v21_native as runner
from scripts.integrations import (
    review_diffusion_planner_v24_single_record_probe as reviewer,
)


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "configs" / "diffusion_planner_v22_native_capability.json"
PLAN = (
    ROOT
    / "docs"
    / "superpowers"
    / "plans"
    / "2026-07-15-v24-fixed-dp-single-record-source-probe.md"
)


def _route(family: str, identity: str, key: str) -> dict:
    return {
        "record_key": key,
        "identity_sha256": identity,
        "map_family_id": family,
        "source_map_path": f"/frozen/{family}.osm",
        "source_map_sha256": "a" * 64,
        "lanelet_ids": [1, 2],
        "route_spec": {
            "map_path": f"/frozen/{family}.osm",
            "lanelet_ids": [1, 2],
            "start_pose": [0.0, 0.0, 0.0],
            "goal_pose": [80.0, 0.0, 0.0],
            "route_length_m": 80.0,
        },
    }


def test_single_record_route_is_selected_only_by_frozen_source_identity() -> None:
    selected = select_probe_route(
        {
            "schema": "diffusion_planner_v24_outcome_blind_route_census_v1",
            "route_census_completed": True,
            "model_loaded": False,
            "candidate_generation_started": False,
            "outcome_accessed": False,
            "holdout_opened": False,
            "retained_routes": [
                _route("family-b", "0" * 64, "b/0"),
                _route("family-a", "f" * 64, "a/f"),
                _route("family-a", "1" * 64, "a/1"),
            ],
        }
    )

    assert selected["record_key"] == "a/1"
    assert selected["map_family_id"] == "family-a"
    assert selected["identity_sha256"] == "1" * 64


def test_probe_config_is_one_tick_k8_and_claim_closed() -> None:
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    selected = _route("family-a", "1" * 64, "a/1")

    config = build_probe_config(
        template,
        selected,
        route_asset_path=Path("/artifact/probe_route.pkl"),
        route_asset_sha256="b" * 64,
    )

    runner.validate_v24_single_record_source_probe_config(config)
    assert config["schema_version"] == "camp_dp_v24_single_record_source_probe_v1"
    assert config["routes"] == [
        {
            "name": "1" * 64,
            "path": "/artifact/probe_route.pkl",
            "sha256": "b" * 64,
        }
    ]
    assert config["seeds"] == {
        "scenario": PROBE_SEED,
        "candidate": PROBE_SEED,
        "bootstrap": PROBE_SEED,
        "formal_forbidden": [11, 12, 13],
    }
    assert config["spawn_config"]["max_steps"] == 1
    assert config["spawn_config"]["seed"] == PROBE_SEED
    assert config["selector"]["candidate_k"] == 8
    assert config["selector"]["selection_policy"] == "v22_source_valid"
    assert config["selector"]["role"] == "v24_read_only_baseline_source_probe"
    assert config["protocol"]["holdout_access_authorized"] is False
    assert config["protocol"]["claim_authorized"] is False
    assert runner._selection_policy(config) == "v22_source_valid"


def test_existing_native_runner_has_narrow_v24_probe_path() -> None:
    validate_source = inspect.getsource(runner._validate_native_config)
    execute_source = inspect.getsource(runner.execute_smoke)
    arm_source = inspect.getsource(runner.build_native_arm_runner)

    assert "camp_dp_v24_single_record_source_probe_v1" in validate_source
    assert "camp_dp_v24_single_record_source_probe_v1" in execute_source
    assert "camp_dp_v24_single_record_source_probe_v1" in arm_source
    assert "max_steps=1" in execute_source


def test_native_evidence_sealer_is_python39_compatible() -> None:
    source = inspect.getsource(runner._seal_evidence)

    assert ".write_text" not in source
    assert source.count('newline="\\n"') == 2


def test_fixed_dp_annotation_compatibility_compiles_without_runtime_union() -> None:
    code = runner._compile_fixed_dp_with_postponed_annotations(
        b"class Marker:\n    pass\nvalue: Marker | None = None\n",
        "/fixed-dp/example.py",
    )
    module = types.ModuleType("fixed_dp_annotation_probe")

    exec(code, module.__dict__)

    assert module.__annotations__["value"] == "Marker | None"


def test_fixed_dp_annotation_finder_is_scoped_to_frozen_repo(tmp_path: Path) -> None:
    dp_repo = tmp_path / "Diffusion-Planner"
    dp_repo.mkdir()
    inside = dp_repo / "inside.py"
    outside = tmp_path / "outside.py"
    inside.write_text("value: int | None = None\n", encoding="utf-8")
    outside.write_text("value: int | None = None\n", encoding="utf-8")
    finder = runner._FixedDpPostponedAnnotationsFinder(dp_repo)

    assert finder.loader_for(inside) is not None
    assert finder.loader_for(outside) is None


def test_fixed_dp_annotation_loader_ignores_cached_bytecode(tmp_path: Path) -> None:
    dp_repo = tmp_path / "Diffusion-Planner"
    dp_repo.mkdir()
    module_path = dp_repo / "cached.py"
    module_path.write_text("value: int | None = None\n", encoding="utf-8")
    standard = importlib.machinery.SourceFileLoader("cached", str(module_path))
    standard.get_code("cached")
    finder = runner._FixedDpPostponedAnnotationsFinder(dp_repo)
    loader = finder.loader_for(module_path, "cached")
    assert loader is not None

    code = loader.get_code("cached")
    module = types.ModuleType("cached")
    exec(code, module.__dict__)

    assert module.__annotations__["value"] == "int | None"


def test_single_record_reviewer_recomputes_k8_contract(tmp_path: Path) -> None:
    rows = [f"{index:064x}" for index in range(8)]
    config = {
        "schema_version": "camp_dp_v24_single_record_source_probe_v1",
        "fixed_dp": {"head": runner.FIXED_DP_HEAD},
        "seeds": {"scenario": PROBE_SEED, "candidate": PROBE_SEED},
        "selector": {"candidate_k": 8},
        "protocol": {
            "holdout_access_authorized": False,
            "claim_authorized": False,
        },
    }
    tick = {
        "candidate_row_sha256": rows,
        "candidate_tensor_sha256_before": "a" * 64,
        "candidate_tensor_sha256_after": "a" * 64,
        "global_rng_sha256_before": "b" * 64,
        "global_rng_sha256_after": "b" * 64,
        "default_candidate0_identity": {
            "candidate0_sha256": rows[0],
            "default_output_sha256": rows[0],
            "elementwise_equal": True,
            "max_abs_difference": 0.0,
            "native_ranked_k8": False,
        },
        "selected_index": 3,
        "selected_trajectory_sha256": rows[3],
        "source_complete_mask": [True] * 8,
        "source_valid_mask": [True] * 8,
        "physical_feasible_mask": [True] * 8,
        "scores": [float(index) for index in range(8)],
        "score_contract": "score_k(w)=a_k^T w",
        "atom_matrix_sha256": "c" * 64,
    }
    summary = {
        "status": "passed",
        "route_count": 1,
        "arm_count": 1,
        "claim_authorized": False,
        "capability_arm": {
            "status": "ok",
            "fixed_dp_head": runner.FIXED_DP_HEAD,
            "scenario_seed": PROBE_SEED,
            "route_sha256": reviewer.EXPECTED_ROUTE_SHA256,
            "runtime_annotation_compatibility": reviewer.EXPECTED_COMPATIBILITY,
            "ticks": [tick],
        },
    }
    execution = {
        "status": "passed",
        "execution_exit": 0,
        "config_sha256": reviewer.EXPECTED_CONFIG_SHA256,
        "outcome_accessed": False,
        "holdout_opened": False,
        "claim_authorized": False,
        "verification": [{"exit": 0}],
    }

    checks = reviewer.evaluate_contract(config, summary, execution)

    assert checks
    assert not [check for check in checks if not check["passed"]]


def test_single_record_probe_plan_keeps_holdout_and_execution_closed() -> None:
    text = " ".join(PLAN.read_text(encoding="utf-8").split())
    for phrase in (
        "lexicographically minimum (map_family_id, identity_sha256, record_key)",
        "seed 24001",
        "exactly one tick",
        "fixed K=8",
        "v22 source-valid selection policy",
        "read-only 14D baseline",
        "candidate 0 identity",
        "preflight must not load the checkpoint",
        "holdout remains unopened",
        "single-record result cannot tune",
    ):
        assert phrase in text
