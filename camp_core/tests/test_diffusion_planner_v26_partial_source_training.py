import copy
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
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _union_fixture(tmp_path: Path) -> tuple[object, Path]:
    module = importlib.import_module(
        "camp_core.integrations.diffusion_planner_v26_partial_source_training"
    )
    kashi = set(module.KASHI_SPEED_METADATA_ORDINALS)
    other_failures = {74, 75, 90, 111, 268, 307, 1276}
    units: list[dict[str, object]] = []
    for ordinal in range(1783):
        if ordinal in kashi:
            family = "legacy_kashiwanoha_cluster"
            corridor = _sha(20_000)
            status = "typed_failure"
            failure_class = "ValueError"
            failure_reason = "route slot 0 requires a positive speed limit"
        else:
            family = f"family_{ordinal % 5}"
            corridor = _sha(20_001 + (ordinal % 154))
            status = "typed_failure" if ordinal in other_failures else "complete"
            failure_class = "NativeReplayFailure" if status == "typed_failure" else None
            failure_reason = "goal_passed" if status == "typed_failure" else None
        units.append(
            {
                "revised_plan_ordinal": ordinal,
                "unit_file_sha256": _sha(30_000 + ordinal),
                "planned_unit_id_sha256": _sha(40_000 + ordinal),
                "route": {
                    "family_id": family,
                    "route_id": f"{family}/route-{ordinal:04d}",
                    "corridor_id": corridor,
                    "parent_ordinal": ordinal,
                    "route_identity_sha256": _sha(50_000 + ordinal),
                    "map_sha256": _sha(60_000 + (ordinal % 6)),
                    "source_artifact_sha256": _sha(70_000 + (ordinal % 6)),
                    "event_manifest_sha256": _sha(80_000 + (ordinal % 6)),
                    "scenario_seed": 46_001 + ordinal,
                },
                "terminal": {
                    "status": status,
                    "failure_class": failure_class,
                    "failure_reason": failure_reason,
                },
            }
        )
    payload = {
        "schema_version": "camp_dp_v26_diversified_training_union_manifest_v1",
        "evidence_role": "development_nonholdout_diversified_training_union",
        "fixed_dp_head": "7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "split": "development_nonholdout",
        "holdout_accessed": False,
        "outcome_fields_consumed": [],
        "denominator": {"planned": 1783, "complete": 1623, "failed": 160, "unattempted": 0},
        "membership": {
            "required_revised_plan_ordinal_range": [0, 1782],
            "exactly_once": True,
            "route_ids_unique": True,
        },
        "units": units,
    }
    path = tmp_path / "immutable_union_manifest.json"
    _write_json(path, payload)
    return module, path


def test_partial_source_manifest_keeps_only_completed_identity_rows(tmp_path: Path) -> None:
    module, union_path = _union_fixture(tmp_path)
    manifest, coverage = module.build_partial_source_training_manifest(
        immutable_union_manifest_path=union_path
    )

    assert manifest["artifact_role"] == "partial-source"
    assert manifest["denominator"] == {
        "planned": 1783,
        "trainable_complete": 1623,
        "typed_failure_excluded": 160,
        "unattempted": 0,
    }
    assert len(manifest["complete_units"]) == 1623
    assert len(manifest["excluded_typed_failures"]) == 160
    assert manifest["training_input_contract"]["generator_topology"]["same_ego_batch_size"] == 8
    assert manifest["training_input_contract"]["generator_topology"]["primary_model_call_count"] == 1
    kashi = [
        row
        for row in manifest["excluded_typed_failures"]
        if row["partial_source_exclusion_class"] == "missing_authoritative_speed_metadata"
    ]
    assert len(kashi) == 153
    assert coverage["source_coverage_accounting"]["planned_family_count"] == 6
    assert coverage["source_coverage_accounting"]["planned_corridor_count"] == 155
    assert coverage["source_coverage_accounting"]["all_key_event_strata_have_retained_complete"] is True
    assert module.validate_training_identity_subset(
        manifest,
        [manifest["complete_units"][0]["planned_unit_id_sha256"]],
    ) == 1
    with pytest.raises(ValueError, match="non-complete identity"):
        module.validate_training_identity_subset(
            manifest,
            [manifest["excluded_typed_failures"][0]["planned_unit_id_sha256"]],
        )


def test_partial_source_manifest_rejects_empty_preplanned_event_stratum(tmp_path: Path) -> None:
    module, union_path = _union_fixture(tmp_path)
    payload = json.loads(union_path.read_text(encoding="utf-8"))
    for unit in payload["units"]:
        if unit["revised_plan_ordinal"] in module.KASHI_SPEED_METADATA_ORDINALS:
            unit["route"]["event_manifest_sha256"] = _sha(99_999)
    _write_json(union_path, payload)

    with pytest.raises(ValueError, match="key event stratum"):
        module.build_partial_source_training_manifest(immutable_union_manifest_path=union_path)


def test_partial_source_cli_materializes_identity_only_zero_call_receipt(tmp_path: Path) -> None:
    module, union_path = _union_fixture(tmp_path)
    cli = importlib.import_module(
        "scripts.integrations.build_diffusion_planner_v26_partial_source_training_manifest"
    )
    output = tmp_path / "partial-source"
    assert cli.main(
        [
            "--immutable-union-manifest", str(union_path),
            "--output-dir", str(output),
            "--expected-camp-head", "a" * 40,
        ]
    ) == 0
    manifest = json.loads((output / "partial_source_training_manifest.json").read_text())
    receipt = json.loads((output / "receipt.json").read_text())
    assert manifest["artifact_role"] == "partial-source"
    assert receipt["artifact_role"] == "partial-source"
    assert all(value == 0 for value in receipt["invocation_counts"].values())
    assert receipt["read_scope"] == {
        "identity_and_terminal_fields_only": True,
        "candidate_payloads_read": False,
        "label_payloads_read": False,
        "trajectory_payloads_read": False,
        "outcome_payloads_read": False,
    }

    invalid = copy.deepcopy(manifest)
    invalid["artifact_role"] = "diversified-six-family-full"
    with pytest.raises(ValueError, match="manifest contract"):
        module.validate_partial_source_training_manifest(invalid)


def test_partial_source_cli_requires_exact_arguments() -> None:
    cli = importlib.import_module(
        "scripts.integrations.build_diffusion_planner_v26_partial_source_training_manifest"
    )
    args = cli.parse_args(
        [
            "--immutable-union-manifest", "union.json",
            "--output-dir", "out",
            "--expected-camp-head", "a" * 40,
        ]
    )
    assert args.immutable_union_manifest == Path("union.json")
    assert args.output_dir == Path("out")
