from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .diffusion_planner_v25_actual_native_receipt_contract import (
    actual_native_receipt_contract,
    actual_native_receipt_contract_sha256,
)
from .diffusion_planner_v25_holdout_contract import (
    canonical_sha256,
    freeze_holdout_identity,
    strict_equal,
    validate_holdout_experiment_protocol,
    validate_holdout_identity,
)
from .diffusion_planner_v25_holdout_plan_dispatch import (
    NONFRESH_CANARY_SPLIT,
    validate_nonfresh_production_equivalence_plan,
)
from .diffusion_planner_v25_fresh_b2 import (
    validate_fresh_b2_manifest_row,
)
from .diffusion_planner_v25_production_equivalence_fixture import (
    validate_nonfresh_map_suite,
)
from .diffusion_planner_v25_signal_complete_runtime import (
    build_signal_complete_scene_adapter,
)


SCHEMA_VERSION = (
    "camp_dp_v25_nonfresh_production_equivalence_authority_v1"
)
STATUS = "frozen_nonfresh_actual_native_production_equivalence_authority"
REVIEW_STATUS = (
    "passed_independent_nonfresh_production_equivalence_authority_review"
)
FILES = {
    "plan": "nonfresh_production_equivalence_plan.json",
    "prepared_runtime": (
        "nonfresh_production_equivalence_prepared_runtime_cases.json"
    ),
    "route_assets": "nonfresh_production_equivalence_route_assets.json",
    "map_suite": "nonfresh_production_equivalence_map_suite.json",
}

_FIELDS = {
    "schema_version",
    "status",
    "implementation_head",
    "fixed_dp_head",
    "critical_implementation_manifest",
    "actual_native_receipt_contract",
    "actual_native_receipt_contract_sha256",
    "holdout_identity",
    "experiment_protocol",
    "execution_plan",
    "prepared_runtime_rows",
    "route_asset_manifest",
    "map_suite",
    "runtime_qualification_rows",
    "upstream_bindings",
    "source_fixture_bindings",
    "frozen_external_assets",
    "scenario_classes",
    "paired_unit_count",
    "arm_run_count",
    "tick_count",
    "nonfresh_provider_only",
    "real_b4_identity_or_rows_used",
    "fresh_identity_cas_created",
    "fresh_outcome_consumed",
    "outcome_fields_consumed",
    "authority_payload_sha256",
}


def freeze_nonfresh_production_equivalence_authority(
    *,
    implementation_head: str,
    fixed_dp_head: str,
    critical_implementation_manifest: Mapping[str, Any],
    experiment_protocol: Mapping[str, Any],
    execution_plan: Mapping[str, Any],
    prepared_runtime_rows: Sequence[Mapping[str, Any]],
    route_asset_manifest: Mapping[str, Any],
    map_suite: Mapping[str, Any],
    runtime_qualification_rows: Sequence[Mapping[str, Any]],
    upstream_bindings: Mapping[str, Mapping[str, Any]],
    source_fixture_bindings: Mapping[str, Mapping[str, Any]],
    frozen_external_assets: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    _git_sha(implementation_head, "implementation_head")
    _git_sha(fixed_dp_head, "fixed_dp_head")
    manifest = _critical_manifest(critical_implementation_manifest)
    protocol = validate_holdout_experiment_protocol(experiment_protocol)
    plan = validate_nonfresh_production_equivalence_plan(execution_plan)
    prepared = _prepared_rows(prepared_runtime_rows, plan=plan)
    qualifications = _qualification_rows(
        runtime_qualification_rows, plan=plan
    )
    routes = _route_assets(route_asset_manifest, plan=plan)
    suite = _map_suite(map_suite)
    bindings = _bindings(upstream_bindings, "upstream")
    fixtures = _bindings(source_fixture_bindings, "source fixture")
    external = _external_assets(frozen_external_assets)
    if (
        plan["split"] != NONFRESH_CANARY_SPLIT
        or manifest["manifest_sha256"]
        != critical_implementation_manifest["manifest_sha256"]
        or set(bindings)
        != {
            "accepted_protocol_preopen",
            "accepted_protocol_preopen_review",
            "training",
            "training_review",
            "calibration_freeze",
            "calibration_freeze_review",
        }
        or set(fixtures)
        != {
            "corrected_full_corpus",
            "corrected_full_corpus_review",
            "formal_source",
            "r0_source",
        }
        or set(external) != {"fixed_dp_args", "probe_template"}
    ):
        raise ValueError("nonFresh production-equivalence authority drifted")
    identity = freeze_holdout_identity(
        split=NONFRESH_CANARY_SPLIT,
        scenario_manifest_sha256=canonical_sha256(qualifications),
        map_suite_payload_sha256=canonical_sha256(suite),
        route_census_sha256=canonical_sha256(routes),
        corridor_census_sha256=canonical_sha256(
            sorted(
                {
                    row["corridor_sha256"]
                    for row in plan["identities"]
                }
            )
        ),
        semantic_census_sha256=canonical_sha256(
            sorted(
                {
                    row["semantic_parameter_block_sha256"]
                    for row in plan["identities"]
                }
            )
        ),
        execution_plan_sha256=plan["plan_payload_sha256"],
        seeds=plan["seeds"],
        arm_order_commit_sha256=canonical_sha256(
            [
                {
                    "unit_sha256": row["unit_sha256"],
                    "ordered_arms": row["ordered_arms"],
                }
                for row in plan["execution_units"]
            ]
        ),
        paired_unit_count=3,
        arm_run_count=9,
        tick_capacity=576,
    )
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "implementation_head": implementation_head,
        "fixed_dp_head": fixed_dp_head,
        "critical_implementation_manifest": manifest,
        "actual_native_receipt_contract": actual_native_receipt_contract(),
        "actual_native_receipt_contract_sha256": (
            actual_native_receipt_contract_sha256()
        ),
        "holdout_identity": identity,
        "experiment_protocol": protocol,
        "execution_plan": plan,
        "prepared_runtime_rows": prepared,
        "route_asset_manifest": routes,
        "map_suite": suite,
        "runtime_qualification_rows": qualifications,
        "upstream_bindings": bindings,
        "source_fixture_bindings": fixtures,
        "frozen_external_assets": external,
        "scenario_classes": [
            "mapped_controlled_override",
            "mapped_observe",
            "no_signal",
        ],
        "paired_unit_count": 3,
        "arm_run_count": 9,
        "tick_count": 576,
        "nonfresh_provider_only": True,
        "real_b4_identity_or_rows_used": False,
        "fresh_identity_cas_created": False,
        "fresh_outcome_consumed": False,
        "outcome_fields_consumed": [],
    }
    result["authority_payload_sha256"] = canonical_sha256(result)
    return validate_nonfresh_production_equivalence_authority(result)


def validate_nonfresh_production_equivalence_authority(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise ValueError(
            "nonFresh production-equivalence authority fields drifted"
        )
    result = json.loads(json.dumps(value))
    _git_sha(result["implementation_head"], "implementation_head")
    _git_sha(result["fixed_dp_head"], "fixed_dp_head")
    manifest = _critical_manifest(result["critical_implementation_manifest"])
    if (
        result["status"] != STATUS
        or result["actual_native_receipt_contract"]
        != actual_native_receipt_contract()
        or result["actual_native_receipt_contract_sha256"]
        != actual_native_receipt_contract_sha256()
        or manifest["manifest_sha256"]
        != result["critical_implementation_manifest"]["manifest_sha256"]
    ):
        raise ValueError("nonFresh production-equivalence ABI drifted")
    plan = validate_nonfresh_production_equivalence_plan(
        result["execution_plan"]
    )
    protocol = validate_holdout_experiment_protocol(
        result["experiment_protocol"]
    )
    identity = validate_holdout_identity(result["holdout_identity"])
    prepared = _prepared_rows(result["prepared_runtime_rows"], plan=plan)
    qualifications = _qualification_rows(
        result["runtime_qualification_rows"], plan=plan
    )
    routes = _route_assets(result["route_asset_manifest"], plan=plan)
    suite = _map_suite(result["map_suite"])
    bindings = _bindings(result["upstream_bindings"], "upstream")
    fixtures = _bindings(
        result["source_fixture_bindings"], "source fixture"
    )
    external = _external_assets(result["frozen_external_assets"])
    expected_identity = freeze_holdout_identity(
        split=NONFRESH_CANARY_SPLIT,
        scenario_manifest_sha256=canonical_sha256(qualifications),
        map_suite_payload_sha256=canonical_sha256(suite),
        route_census_sha256=canonical_sha256(routes),
        corridor_census_sha256=canonical_sha256(
            sorted(
                {
                    row["corridor_sha256"]
                    for row in plan["identities"]
                }
            )
        ),
        semantic_census_sha256=canonical_sha256(
            sorted(
                {
                    row["semantic_parameter_block_sha256"]
                    for row in plan["identities"]
                }
            )
        ),
        execution_plan_sha256=plan["plan_payload_sha256"],
        seeds=plan["seeds"],
        arm_order_commit_sha256=canonical_sha256(
            [
                {
                    "unit_sha256": row["unit_sha256"],
                    "ordered_arms": row["ordered_arms"],
                }
                for row in plan["execution_units"]
            ]
        ),
        paired_unit_count=3,
        arm_run_count=9,
        tick_capacity=576,
    )
    if not strict_equal(identity, expected_identity):
        raise ValueError("nonFresh production-equivalence identity drifted")
    if (
        set(bindings)
        != {
            "accepted_protocol_preopen",
            "accepted_protocol_preopen_review",
            "training",
            "training_review",
            "calibration_freeze",
            "calibration_freeze_review",
        }
        or set(fixtures)
        != {
            "corrected_full_corpus",
            "corrected_full_corpus_review",
            "formal_source",
            "r0_source",
        }
        or set(external) != {"fixed_dp_args", "probe_template"}
    ):
        raise ValueError("nonFresh production-equivalence bindings drifted")
    exact = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "scenario_classes": [
            "mapped_controlled_override",
            "mapped_observe",
            "no_signal",
        ],
        "paired_unit_count": 3,
        "arm_run_count": 9,
        "tick_count": 576,
        "nonfresh_provider_only": True,
        "real_b4_identity_or_rows_used": False,
        "fresh_identity_cas_created": False,
        "fresh_outcome_consumed": False,
        "outcome_fields_consumed": [],
    }
    for name, expected in exact.items():
        if not strict_equal(result[name], expected):
            raise ValueError(
                f"nonFresh production-equivalence {name} drifted"
            )
    payload = dict(result)
    stored = payload.pop("authority_payload_sha256")
    if stored != canonical_sha256(payload):
        raise ValueError(
            "nonFresh production-equivalence authority SHA drifted"
        )
    return result


def _critical_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    if (
        type(value) is not dict
        or set(value) != {"schema_version", "paths", "manifest_sha256"}
        or type(value["paths"]) is not list
        or not value["paths"]
    ):
        raise ValueError("critical implementation manifest drifted")
    if value["manifest_sha256"] != canonical_sha256(value["paths"]):
        raise ValueError("critical implementation manifest SHA drifted")
    return json.loads(json.dumps(value))


def _bindings(
    value: Mapping[str, Mapping[str, Any]], label: str
) -> dict[str, dict[str, str]]:
    if type(value) is not dict or not value:
        raise ValueError(f"{label} bindings must be nonempty")
    result: dict[str, dict[str, str]] = {}
    for role, binding in value.items():
        if (
            type(role) is not str
            or not role
            or type(binding) is not dict
            or set(binding) != {"path", "root_sha256"}
        ):
            raise ValueError(f"{label} binding schema drifted")
        path = _absolute_path(binding["path"], f"{label} path")
        _sha(binding["root_sha256"], f"{label} root")
        result[role] = {
            "path": path,
            "root_sha256": binding["root_sha256"],
        }
    return dict(sorted(result.items()))


def _external_assets(
    value: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, str]]:
    if type(value) is not dict or not value:
        raise ValueError("external assets must be nonempty")
    result: dict[str, dict[str, str]] = {}
    for role, asset in value.items():
        if (
            type(role) is not str
            or not role
            or type(asset) is not dict
            or set(asset) != {"path", "sha256"}
        ):
            raise ValueError("external asset schema drifted")
        result[role] = {
            "path": _absolute_path(asset["path"], "external asset path"),
            "sha256": asset["sha256"],
        }
        _sha(result[role]["sha256"], "external asset SHA")
    return dict(sorted(result.items()))


def _prepared_rows(
    value: Sequence[Mapping[str, Any]], *, plan: Mapping[str, Any]
) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) != 3:
        raise ValueError("prepared runtime denominator drifted")
    identities = plan["identities"]
    result: list[dict[str, Any]] = []
    for identity, raw in zip(identities, value, strict=True):
        if type(raw) is not dict:
            raise ValueError("prepared runtime row type drifted")
        row = json.loads(json.dumps(raw))
        if (
            row.get("identity_ordinal") != identity["identity_ordinal"]
            or row.get("scenario_identity_sha256")
            != identity["scenario_identity_sha256"]
            or row.get("semantic_parameter_block_sha256")
            != identity["semantic_parameter_block_sha256"]
            or row.get("fresh_b2_opened") is not False
            or row.get("outcome_fields_consumed") != []
        ):
            raise ValueError("prepared runtime authority drifted")
        adapter = build_signal_complete_scene_adapter(row)
        if (
            adapter.case["route_identity_sha256"]
            != identity["route_identity_sha256"]
            or adapter.case["source_map_sha256"] != identity["map_sha256"]
            or adapter.case["signal_source_class"]
            != identity["signal_source_class"]
            or adapter.case["phase_authority_mode"]
            != identity["phase_authority_mode"]
        ):
            raise ValueError("prepared runtime/plan binding drifted")
        result.append(row)
    return result


def _qualification_rows(
    value: Sequence[Mapping[str, Any]], *, plan: Mapping[str, Any]
) -> list[dict[str, Any]]:
    if type(value) is not list or len(value) != 3:
        raise ValueError("runtime qualification denominator drifted")
    result: list[dict[str, Any]] = []
    for index, (identity, raw) in enumerate(
        zip(plan["identities"], value, strict=True)
    ):
        row = validate_fresh_b2_manifest_row(raw, index=index)
        expected = {
            "map_geometry_sha256": identity["map_geometry_sha256"],
            "map_file_sha256": identity["map_sha256"],
            "intersection_sha256": identity["intersection_sha256"],
            "corridor_sha256": identity["corridor_sha256"],
            "route_family_sha256": identity["route_family_sha256"],
            "semantic_parameter_block_sha256": identity[
                "semantic_parameter_block_sha256"
            ],
            "route_identity_sha256": identity["route_identity_sha256"],
            "benchmark_stratum": identity["benchmark_stratum"],
            "scenario_family": identity["scenario_family"],
            "tier": identity["risk_tier"],
            "signal_source_class": identity["signal_source_class"],
            "phase_authority_mode": identity["phase_authority_mode"],
            "source_chain": identity["source_chain"],
            "route_length_m": identity["route_length_m"],
        }
        if any(not strict_equal(row[name], item) for name, item in expected.items()):
            raise ValueError("runtime qualification/plan binding drifted")
        result.append(row)
    return result


def _route_assets(
    value: Mapping[str, Any], *, plan: Mapping[str, Any]
) -> dict[str, Any]:
    fields = {
        "schema_version",
        "status",
        "split",
        "route_count",
        "map_count",
        "route_assets",
        "route_asset_sha256",
        "fixed_dp_modified",
        "map_semantics_modified",
        "model_loaded",
        "candidate_generation_executed",
        "fresh_b2_opened",
        "outcome_fields_consumed",
    }
    if type(value) is not dict or set(value) != fields:
        raise ValueError("nonFresh route asset manifest fields drifted")
    rows = value["route_assets"]
    exact = {
        "schema_version": "camp_dp_v25_signal_complete_route_assets_v1",
        "status": "materialized_signal_complete_fixed_dp_routes",
        "split": NONFRESH_CANARY_SPLIT,
        "route_count": 3,
        "map_count": plan["map_count"],
        "fixed_dp_modified": False,
        "map_semantics_modified": False,
        "model_loaded": False,
        "candidate_generation_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    if any(not strict_equal(value[name], expected) for name, expected in exact.items()):
        raise ValueError("nonFresh route asset manifest contract drifted")
    if type(rows) is not list or len(rows) != 3:
        raise ValueError("nonFresh route asset denominator drifted")
    if value["route_asset_sha256"] != canonical_sha256(rows):
        raise ValueError("nonFresh route asset row root drifted")
    for identity, row in zip(plan["identities"], rows, strict=True):
        if (
            type(row) is not dict
            or row.get("route_identity_sha256")
            != identity["route_identity_sha256"]
            or row.get("scenario_identity_sha256")
            != identity["scenario_identity_sha256"]
            or row.get("map_sha256") != identity["map_sha256"]
            or row.get("map_geometry_sha256")
            != identity["map_geometry_sha256"]
            or row.get("corridor_sha256") != identity["corridor_sha256"]
            or row.get("source_chain_sha256")
            != identity["source_chain_sha256"]
            or row.get("route_lanelet_ids")
            != identity["route_spec"]["lanelet_ids"]
            or row.get("fresh_b2_opened") is not False
            or row.get("outcome_fields_consumed") != []
        ):
            raise ValueError("nonFresh route asset row authority drifted")
        asset = row.get("route_asset")
        if (
            type(asset) is not dict
            or set(asset) != {"name", "path", "sha256"}
            or asset["name"] != identity["route_identity_sha256"]
        ):
            raise ValueError("nonFresh route asset binding drifted")
        path = Path(asset["path"])
        if (
            not path.is_absolute()
            or path.is_symlink()
            or not path.is_file()
            or _file_sha256(path) != asset["sha256"]
        ):
            raise ValueError("nonFresh route asset bytes drifted")
    return json.loads(json.dumps(value))


def _map_suite(value: Mapping[str, Any]) -> dict[str, Any]:
    if (
        type(value) is not dict
        or type(value.get("maps")) is not list
        or not value["maps"]
    ):
        raise ValueError("nonFresh map suite drifted")
    first = Path(value["maps"][0]["path"]).resolve()
    root = first.parents[1]
    return validate_nonfresh_map_suite(value, map_artifact=root)


def _absolute_path(value: Any, label: str) -> str:
    if type(value) is not str:
        raise ValueError(f"{label} must be a string")
    path = Path(value)
    if not path.is_absolute() or str(path) != str(path.resolve()):
        raise ValueError(f"{label} must be canonical and absolute")
    return str(path)


def _git_sha(value: Any, label: str) -> None:
    if (
        type(value) is not str
        or len(value) != 40
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{label} must be a lowercase git SHA")


def _sha(value: Any, label: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
    ):
        raise ValueError(f"{label} must be a lowercase SHA256")


def _file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
