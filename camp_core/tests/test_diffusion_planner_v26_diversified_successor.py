from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _sha(index: int) -> str:
    return f"{index:064x}"


def _schedule(index: int) -> dict[str, object]:
    family = f"family_{index % 6}"
    return {
        "family_id": family,
        "route_id": f"{family}/route-{index:04d}",
        "corridor_id": _sha(20_000 + (index % 155)),
        "parent_ordinal": index,
        "source_artifact_sha256": _sha(30_000 + (index % 6)),
        "event_manifest_sha256": _sha(40_000 + (index % 6)),
        "route_record": {
            "identity_sha256": _sha(50_000 + index),
            "source_map_sha256": _sha(60_000 + (index % 6)),
            "source_geometry_sha256": _sha(70_000 + index),
            "source_map_path": f"/immutable/maps/{index % 6}.osm",
            "lanelet_ids": [index + 1],
            "source_stratum": {
                "traffic_light": index % 2 == 0,
                "branch_intersection": index % 3 == 0,
                "tight_corridor": True,
                "short_progress_opportunity": index % 5 == 0,
            },
        },
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _parent_fixture(tmp_path: Path):
    successor = importlib.import_module(
        "camp_core.integrations.diffusion_planner_v26_diversified_successor"
    )
    routes = [_schedule(index) for index in range(1783)]
    parent_plan = {
        "schema_version": "camp_dp_v26_diversified_route_plan_revision_v1",
        "evidence_role": "development_nonholdout_diversified_training_route_plan_revision",
        "fixed_dp_head": "7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "split": "development_nonholdout",
        "holdout_accessed": False,
        "outcome_fields_consumed": [],
        "route_plan_sha256": _sha(1),
        "denominator": {"planned": 1783, "complete": 0, "failed": 0, "unattempted": 1783},
        "family_projections": [{"family_id": f"family_{index}"} for index in range(6)],
        "routes": routes,
    }
    parent_plan_path = tmp_path / "revised_plan.json"
    _write_json(parent_plan_path, parent_plan)
    root = tmp_path / "recovered"
    root.mkdir()
    _write_json(root / "manifest.json", {"route_plan_sha256": _sha(1)})
    _write_json(
        root / "report.json",
        {
            "route_plan_sha256": _sha(1),
            "denominator": {"planned": 1783, "complete": 479, "failed": 6, "unattempted": 1298},
        },
    )
    _write_json(root / "raw_receipt.json", {"fixture": True})
    _write_json(root / "recovery_receipt.json", {"fixture": True})
    _write_json(root / "recovery.status.json", {"fixture": True})
    failed = {74: ("ValueError", "source_projection"), 75: ("ValueError", "source_projection"), 90: ("NativeReplayFailure", "goal_passed"), 111: ("NativeReplayFailure", "goal_reached"), 268: ("NativeReplayFailure", "goal_passed"), 307: ("NativeReplayFailure", "goal_reached")}
    for index, schedule in enumerate(routes):
        record = schedule["route_record"]
        if index <= 484:
            status = "typed_failure" if index in failed else "complete"
        else:
            status = "unattempted"
        failure_class, failure_reason = failed.get(index, (None, None))
        _write_json(
            root / "units" / f"{index:04d}.json",
            {
                "unit_index": index,
                "planned_unit_id_sha256": _sha(80_000 + index),
                "route": {
                    "family_id": schedule["family_id"],
                    "route_id": schedule["route_id"],
                    "corridor_id": schedule["corridor_id"],
                    "parent_ordinal": index,
                    "route_identity_sha256": record["identity_sha256"],
                    "map_sha256": record["source_map_sha256"],
                    "source_artifact_sha256": schedule["source_artifact_sha256"],
                    "event_manifest_sha256": schedule["event_manifest_sha256"],
                    "scenario_seed": successor.SCENARIO_SEED_BASE + index,
                },
                "terminal": {
                    "status": status,
                    "failure_class": failure_class,
                    "failure_reason": failure_reason,
                },
            },
        )
    return successor, parent_plan_path, root


def _prior_attempt_fixture(tmp_path: Path, plan: dict[str, object]) -> Path:
    root = tmp_path / "prior-attempt"
    denominator = {"planned": 1298, "complete": 0, "failed": 1, "unattempted": 1297}
    _write_json(root / "manifest.json", {"successor_plan_sha256": plan["route_plan_sha256"]})
    _write_json(
        root / "raw_receipt.json",
        {"successor_plan_sha256": plan["route_plan_sha256"], "denominator": denominator},
    )
    _write_json(
        root / "report.json",
        {
            "route_plan_sha256": plan["route_plan_sha256"],
            "status": "terminal_no_trainable_pools",
            "denominator": denominator,
        },
    )
    _write_json(root / "run.status.json", {"status": "terminal", "denominator": denominator})
    (root / "run.exit").parent.mkdir(parents=True, exist_ok=True)
    (root / "run.exit").write_bytes(b"0\n")
    _write_json(
        root / "units" / "0485.json",
        {
            "unit_index": 485,
            "terminal": {
                "status": "typed_failure",
                "failure_class": "ParentExecutionException",
            },
            "parent_exception_boundary": {
                "revised_plan_ordinal": 485,
                "phase": "native_same_ego_b8_replay",
            },
        },
    )
    return root


def test_successor_plan_retains_exact_tail_coverage_and_seed(tmp_path: Path) -> None:
    successor, parent_plan_path, recovered_root = _parent_fixture(tmp_path)
    material = successor.build_successor_plan(
        parent_revised_plan_path=parent_plan_path, parent_recovered_root=recovered_root
    )
    plan = material["route_plan"]
    assert len(plan["routes"]) == 1298
    assert [row["revised_plan_ordinal"] for row in plan["routes"]] == list(range(485, 1783))
    assert plan["routes"][0]["route_id"].endswith("route-0485")
    assert plan["routes"][0]["scenario_seed"] == 46486
    assert plan["union_contract"]["retained_denominator"] == {
        "complete": 479,
        "failed": 6,
        "unattempted": 0,
    }
    assert len(plan["retained_parent_interval"]["typed_failure_identities"]) == 6
    assert material["parent_coverage"]["denominator"] == {
        "planned": 485,
        "complete": 479,
        "failed": 6,
        "unattempted": 0,
    }

    output = tmp_path / "successor-plan"
    paths = successor.materialize_successor_plan(
        parent_revised_plan_path=parent_plan_path,
        parent_recovered_root=recovered_root,
        output_dir=output,
        camp_head="a" * 40,
    )
    verified = successor.load_verified_successor_plan(
        successor_plan_path=paths["plan"],
        parent_revised_plan_path=parent_plan_path,
        parent_recovered_root=recovered_root,
    )
    assert verified["route_plan"] == plan

    tampered = copy.deepcopy(plan)
    tampered["routes"][0], tampered["routes"][1] = tampered["routes"][1], tampered["routes"][0]
    with pytest.raises(ValueError, match="exact parent-evidence continuation"):
        successor.validate_successor_plan(
            value=tampered,
            parent_revised_plan_path=parent_plan_path,
            parent_recovered_root=recovered_root,
        )


def test_successor_parent_exception_is_atomic_and_leaves_tail_unattempted(tmp_path: Path) -> None:
    successor, parent_plan_path, recovered_root = _parent_fixture(tmp_path)
    material = successor.build_successor_plan(
        parent_revised_plan_path=parent_plan_path, parent_recovered_root=recovered_root
    )
    runner = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_diversified_successor_acquisition"
    )
    plan = material["route_plan"]
    ledger = runner._SuccessorLedger(
        output_dir=tmp_path / "successor-acquisition",
        manifest={
            "camp_head": "a" * 40,
            "route_plan_sha256": plan["route_plan_sha256"],
            "successor_plan_sha256": plan["route_plan_sha256"],
            "parent_revised_plan_sha256": plan["parent_revised_plan"]["route_plan_sha256"],
        },
        route_plan=plan,
    )
    boundary = plan["routes"][0]
    assert ledger.record_parent_exception_boundary(
        ordinal=485,
        schedule=boundary,
        scenario_seed=boundary["scenario_seed"],
        phase="model_initialization",
        exc=RuntimeError("fixture outer stop"),
    )
    ledger.finalize(terminal_error="RuntimeError: fixture outer stop")
    first = json.loads((tmp_path / "successor-acquisition" / "units" / "0485.json").read_text())
    later = json.loads((tmp_path / "successor-acquisition" / "units" / "0486.json").read_text())
    report = json.loads((tmp_path / "successor-acquisition" / "report.json").read_text())
    assert first["terminal"]["failure_class"] == "ParentExecutionException"
    assert first["parent_exception_boundary"]["phase"] == "model_initialization"
    assert later["terminal"]["status"] == "unattempted"
    assert report["denominator"] == {"planned": 1298, "complete": 0, "failed": 1, "unattempted": 1297}


def test_union_manifest_has_each_revised_ordinal_exactly_once(tmp_path: Path) -> None:
    successor, parent_plan_path, recovered_root = _parent_fixture(tmp_path)
    plan_root = tmp_path / "successor-plan"
    paths = successor.materialize_successor_plan(
        parent_revised_plan_path=parent_plan_path,
        parent_recovered_root=recovered_root,
        output_dir=plan_root,
        camp_head="a" * 40,
    )
    plan = json.loads(paths["plan"].read_text())
    prior_attempt = _prior_attempt_fixture(tmp_path, plan)
    acquisition = tmp_path / "successor-acquisition"
    acquisition.mkdir()
    for name in ("manifest.json", "raw_receipt.json", "report.json", "run.status.json"):
        _write_json(acquisition / name, {"fixture": True})
    (acquisition / "run.exit").write_text("0\n", encoding="utf-8")
    for schedule in plan["routes"]:
        ordinal = schedule["revised_plan_ordinal"]
        record = schedule["route_record"]
        _write_json(
            acquisition / "units" / f"{ordinal:04d}.json",
            {
                "unit_index": ordinal,
                "planned_unit_id_sha256": _sha(90_000 + ordinal),
                "route": {
                    "family_id": schedule["family_id"],
                    "route_id": schedule["route_id"],
                    "corridor_id": schedule["corridor_id"],
                    "revised_plan_ordinal": ordinal,
                    "parent_ordinal": schedule["parent_ordinal"],
                    "route_identity_sha256": record["identity_sha256"],
                    "map_sha256": record["source_map_sha256"],
                    "source_artifact_sha256": schedule["source_artifact_sha256"],
                    "event_manifest_sha256": schedule["event_manifest_sha256"],
                    "scenario_seed": schedule["scenario_seed"],
                },
                "terminal": {"status": "complete", "failure_class": None, "failure_reason": None},
            },
        )
    union = successor.materialize_immutable_union_manifest(
        successor_plan_path=paths["plan"],
        parent_revised_plan_path=parent_plan_path,
        parent_recovered_root=recovered_root,
        successor_acquisition_root=acquisition,
        output_dir=tmp_path / "union",
        prior_attempt_root=prior_attempt,
    )
    payload = json.loads(union.read_text())
    assert payload["denominator"] == {"planned": 1783, "complete": 1777, "failed": 6, "unattempted": 0}
    assert [item["revised_plan_ordinal"] for item in payload["units"]] == list(range(1783))
    assert payload["prior_attempt_history"]["role"] == "immutable_prior_attempt_history_only"
    assert payload["prior_attempt_history"]["scientific_route_identity_replayed"] is False


def test_successor_qualification_aggregate_requires_exact_tail_and_zero_model() -> None:
    qualification = importlib.import_module(
        "scripts.integrations.qualify_diffusion_planner_v26_diversified_successor_pre_model"
    )
    units = [
        {
            "revised_plan_ordinal": ordinal,
            "route": {
                "route_id": f"route-{ordinal}",
                "family_id": f"family-{ordinal % 6}",
                "corridor_id": f"corridor-{ordinal % 155}",
            },
            "terminal": {"status": "qualified"},
        }
        for ordinal in range(485, 1783)
    ]
    receipt = qualification._aggregate(
        manifest={"successor_plan_sha256": _sha(1), "parent_revised_plan_sha256": _sha(2)},
        units=units,
        terminal_error=None,
    )
    assert receipt["status"] == "passed"
    assert receipt["acquisition_authorized"] is True
    assert receipt["zero_model_totals"]["model_forward_count"] == 0
    units[-1]["terminal"]["status"] = "failed"
    assert qualification._aggregate(
        manifest={"successor_plan_sha256": _sha(1), "parent_revised_plan_sha256": _sha(2)},
        units=units,
        terminal_error=None,
    )["status"] == "failed"


def test_successor_parsers_require_explicit_parent_and_tail_bindings() -> None:
    prepare = importlib.import_module(
        "scripts.integrations.prepare_diffusion_planner_v26_diversified_successor_plan"
    )
    qualify = importlib.import_module(
        "scripts.integrations.qualify_diffusion_planner_v26_diversified_successor_pre_model"
    )
    acquire = importlib.import_module(
        "scripts.integrations.run_diffusion_planner_v26_diversified_successor_acquisition"
    )
    plan_args = prepare.parse_args(
        [
            "--parent-revised-plan", "parent.json",
            "--parent-recovered-root", "recovered",
            "--output-dir", "out",
            "--expected-camp-head", "a" * 40,
            "--expected-parent-revised-plan-sha256", "b" * 64,
        ]
    )
    assert plan_args.parent_recovered_root == Path("recovered")
    qual_args = qualify.parse_args(
        [
            "--output-dir", "qual",
            "--qualification-lock", "lock",
            "--successor-plan", "successor.json",
            "--parent-revised-plan", "parent.json",
            "--parent-recovered-root", "recovered",
            "--prior-terminal-attempt-root", "prior-attempt",
            "--expected-successor-plan-sha256", "b" * 64,
            "--base-probe-config", "base.json",
            "--reference-weights", "weights",
            "--reference-weights-root", "c" * 64,
            "--reference-weights-review", "review.json",
            "--reference-weights-review-root", "d" * 64,
            "--fixed-dp-repo", "fixed",
            "--expected-camp-head", "a" * 40,
        ]
    )
    assert qual_args.expected_successor_plan_sha256 == "b" * 64
    acquire_args = acquire.parse_args(
        [
            "--output-dir", "acquisition",
            "--union-output-dir", "union",
            "--worker-lock", "worker.lock",
            "--successor-plan", "successor.json",
            "--parent-revised-plan", "parent.json",
            "--parent-recovered-root", "recovered",
            "--prior-terminal-attempt-root", "prior-attempt",
            "--expected-successor-plan-sha256", "b" * 64,
            "--base-probe-config", "base.json",
            "--reference-weights", "weights",
            "--reference-weights-root", "c" * 64,
            "--reference-weights-review", "review.json",
            "--reference-weights-review-root", "d" * 64,
            "--fixed-dp-repo", "fixed",
            "--expected-camp-head", "a" * 40,
            "--pre-model-qualification", "qual/raw_receipt.json",
        ]
    )
    assert acquire_args.union_output_dir == Path("union")
