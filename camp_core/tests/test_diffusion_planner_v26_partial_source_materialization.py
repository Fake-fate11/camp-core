import hashlib
import importlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "camp_core"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def _sha(index: int) -> str:
    return f"{index:064x}"


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _route(ordinal: int) -> dict[str, object]:
    return {
        "family_id": f"family-{ordinal}",
        "route_id": f"route-{ordinal}",
        "corridor_id": _sha(10_000 + ordinal),
        "parent_ordinal": ordinal,
        "route_identity_sha256": _sha(11_000 + ordinal),
        "map_sha256": _sha(12_000 + ordinal),
        "source_artifact_sha256": _sha(13_000 + ordinal),
        "event_manifest_sha256": _sha(14_000 + ordinal),
        "scenario_seed": 46_001 + ordinal,
    }


def _unit(ordinal: int) -> dict[str, object]:
    return {
        "unit_index": ordinal,
        "planned_unit_id_sha256": _sha(20_000 + ordinal),
        "route": _route(ordinal),
        "terminal": {"status": "complete", "failure_class": None, "failure_reason": None},
        "training_pool": {},
    }


def _fixture(tmp_path: Path) -> tuple[object, dict[str, object], dict[int, dict[str, object]], Path]:
    module = importlib.import_module(
        "camp_core.integrations.diffusion_planner_v26_partial_source_materialization"
    )
    parent = tmp_path / "parent"
    successor = tmp_path / "successor"
    unit0 = _unit(0)
    unit485 = _unit(485)
    path0 = parent / "units" / "0000.json"
    path485 = successor / "units" / "0485.json"
    _write_json(path0, unit0)
    _write_json(path485, unit485)
    hash0 = hashlib.sha256(path0.read_bytes()).hexdigest()
    hash485 = hashlib.sha256(path485.read_bytes()).hexdigest()
    union_units: list[dict[str, object]] = [{} for _ in range(486)]
    union_units[0] = {
        "revised_plan_ordinal": 0,
        "planned_unit_id_sha256": unit0["planned_unit_id_sha256"],
        "unit_file_sha256": hash0,
        "route": unit0["route"],
        "terminal": unit0["terminal"],
    }
    union_units[485] = {
        "revised_plan_ordinal": 485,
        "planned_unit_id_sha256": unit485["planned_unit_id_sha256"],
        "unit_file_sha256": hash485,
        "route": unit485["route"],
        "terminal": unit485["terminal"],
    }
    selected = {
        0: {
            "revised_plan_ordinal": 0,
            "planned_unit_id_sha256": unit0["planned_unit_id_sha256"],
            "unit_file_sha256": hash0,
            "route": unit0["route"],
        },
        485: {
            "revised_plan_ordinal": 485,
            "planned_unit_id_sha256": unit485["planned_unit_id_sha256"],
            "unit_file_sha256": hash485,
            "route": unit485["route"],
        },
    }
    union = {
        "parent_recovered_root": {"path": str(parent)},
        "successor_acquisition_root": {"path": str(successor)},
        "units": union_units,
    }
    return module, union, selected, path485


def test_collect_complete_units_uses_only_receipt_bound_parent_and_successor_ledgers(
    tmp_path: Path,
) -> None:
    module, union, selected, _path485 = _fixture(tmp_path)
    complete, provenance = module._collect_complete_units(
        union=union, selected_by_ordinal=selected, expected_count=2
    )

    assert [unit["unit_index"] for unit in complete] == [0, 485]
    assert [item["source_root_role"] for item in provenance["source_units"]] == [
        "parent_recovered",
        "successor_acquisition",
    ]
    assert len(provenance["selected_unit_hash_manifest_sha256"]) == 64


def test_collect_complete_units_rejects_atomic_byte_hash_drift(tmp_path: Path) -> None:
    module, union, selected, path485 = _fixture(tmp_path)
    payload = json.loads(path485.read_text(encoding="utf-8"))
    payload["training_pool"] = {"unexpected": True}
    _write_json(path485, payload)

    with pytest.raises(ValueError, match="byte hash drifted"):
        module._collect_complete_units(
            union=union, selected_by_ordinal=selected, expected_count=2
        )


def test_materializer_cli_requires_final_population_receipt() -> None:
    cli = importlib.import_module(
        "scripts.integrations.materialize_diffusion_planner_v26_partial_source_training_rows"
    )
    args = cli.parse_args(
        [
            "--final-population-receipt",
            "population.json",
            "--output-dir",
            "rows",
            "--expected-camp-head",
            "a" * 40,
        ]
    )
    assert args.final_population_receipt == Path("population.json")
    assert args.output_dir == Path("rows")
