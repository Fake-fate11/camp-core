#!/usr/bin/env python3
"""Independently review the sealed Fresh B3 production-composition preflight."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_b3_preopen import (
    FIXED_DP_HEAD,
    build_b3_experiment_protocol,
    build_b3_holdout_identity,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
    canonical_json_bytes,
    canonical_sha256,
    strict_equal,
    validate_forward_binding,
    validate_latency_namespaces,
)
from camp_core.integrations.diffusion_planner_v25_holdout_execution import (
    validate_holdout_arm_config,
)
from camp_core.integrations.diffusion_planner_v25_holdout_preflight import (
    validate_nonfresh_preflight_authority,
)
from camp_core.integrations.diffusion_planner_v25_holdout_protocol import (
    derive_protocol_assets_from_accepted_preopen,
    validate_protocol_assets_receipt,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (
    build_signal_complete_suite,
    validate_signal_complete_suite,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
)
from scripts.integrations.review_diffusion_planner_v25_holdout_production_preflight import (
    _independent_review,
)


SCHEMA_VERSION = (
    "camp_dp_v25_fresh_b3_production_preflight_independent_review_v1"
)


def review(
    *,
    source_artifact: Path,
    source_root_sha256: str,
    output_dir: Path,
) -> str:
    source = source_artifact.resolve()
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    seal = verify_complete_seal(
        source, source_root_sha256, label="Fresh B3 production preflight"
    )
    required = {
        "COMMAND",
        "HEADS",
        "b3_execution_plan.json",
        "b3_map_suite.json",
        "experiment_protocol.json",
        "holdout_identity.json",
        "preflight.json",
        "protocol_assets.json",
        "protocol_assets_receipt.json",
        "nonfresh_preflight_authority.json",
        "fixture_binding.json",
        "report.json",
        "run.exit",
        "configs/candidate0.json",
        "configs/static14d.json",
        "configs/scene14d.json",
        "runs/candidate0/native_receipt.json",
        "runs/candidate0/decision_evidence.json",
        "runs/static14d/native_receipt.json",
        "runs/static14d/decision_evidence.json",
        "runs/scene14d/native_receipt.json",
        "runs/scene14d/decision_evidence.json",
        "runs/candidate0_supplementary/native_receipt.json",
    }
    actual_paths = set(seal["manifest_paths"])
    if not required.issubset(actual_paths) or any(
        path not in required
        and not any(
            path.startswith(prefix)
            for prefix in (
                "runs/candidate0/native/",
                "runs/static14d/native/",
                "runs/scene14d/native/",
                "runs/candidate0_supplementary/native/",
            )
        )
        for path in actual_paths
    ):
        raise ValueError("Fresh B3 production preflight inventory drifted")
    for prefix in (
        "runs/candidate0/native/",
        "runs/static14d/native/",
        "runs/scene14d/native/",
        "runs/candidate0_supplementary/native/",
    ):
        if not any(path.startswith(prefix) for path in actual_paths):
            raise ValueError(f"Fresh B3 production preflight missing {prefix}")
    if (source / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh B3 production preflight did not pass")
    suite = build_signal_complete_suite("fresh_b3")
    expected_suite = validate_signal_complete_suite(suite)
    plan = build_signal_complete_execution_plan("fresh_b3")
    identity = build_b3_holdout_identity(suite=suite, plan=plan)
    assets = _canonical_object(source / "protocol_assets.json")
    protocol_receipt = validate_protocol_assets_receipt(
        _canonical_object(source / "protocol_assets_receipt.json")
    )
    independently_derived_assets, independently_derived_receipt = (
        derive_protocol_assets_from_accepted_preopen(
            preopen_artifact=Path(
                protocol_receipt["accepted_preopen"]["path"]
            ),
            preopen_root_sha256=protocol_receipt["accepted_preopen"][
                "root_sha256"
            ],
            preopen_review_artifact=Path(
                protocol_receipt["accepted_preopen_review"]["path"]
            ),
            preopen_review_root_sha256=protocol_receipt[
                "accepted_preopen_review"
            ]["root_sha256"],
        )
    )
    if (
        not strict_equal(protocol_receipt["protocol_assets"], assets)
        or not strict_equal(independently_derived_assets, assets)
        or not strict_equal(
            independently_derived_receipt, protocol_receipt
        )
    ):
        raise ValueError("Fresh B3 protocol asset derivation receipt drifted")
    protocol = build_b3_experiment_protocol(assets)
    for path, expected in (
        ("b3_map_suite.json", expected_suite),
        ("b3_execution_plan.json", plan),
        ("holdout_identity.json", identity),
        ("experiment_protocol.json", protocol),
    ):
        if not strict_equal(_canonical_object(source / path), expected):
            raise ValueError(f"Fresh B3 production preflight {path} drifted")
    payload = _canonical_object(source / "preflight.json")
    authority = validate_nonfresh_preflight_authority(
        _canonical_object(source / "nonfresh_preflight_authority.json"),
        holdout_identity_sha256=identity["holdout_identity_sha256"],
        experiment_protocol_sha256=protocol["experiment_protocol_sha256"],
    )
    if payload["nonfresh_preflight_authority"] != authority:
        raise ValueError("Fresh B3 preflight authority payload drifted")
    configs = {
        arm: validate_holdout_arm_config(
            _canonical_object(source / "configs" / f"{arm}.json")
        )
        for arm in ("candidate0", "static14d", "scene14d")
    }
    if payload["config_payloads"] != configs:
        raise ValueError("Fresh B3 preflight config projection drifted")
    primary = {
        arm: _canonical_object(
            source / "runs" / arm / "native_receipt.json"
        )
        for arm in ("candidate0", "static14d", "scene14d")
    }
    diagnostic = _canonical_object(
        source
        / "runs"
        / "candidate0_supplementary"
        / "native_receipt.json"
    )
    decision_evidence = {
        arm: _canonical_value(
            source / "runs" / arm / "decision_evidence.json"
        )
        for arm in ("candidate0", "static14d", "scene14d")
    }
    _review_actual_native_composition(
        payload=payload,
        configs=configs,
        primary=primary,
        diagnostic=diagnostic,
        decision_evidence=decision_evidence,
    )
    independent = _independent_review(
        payload,
        source_root_sha256=source_root_sha256,
        callback_oracle="real_native",
    )
    report = _canonical_object(source / "report.json")
    if (
        report.get("status")
        != "passed_fresh_b3_nonfresh_exact_production_preflight"
        or report.get("holdout_identity_sha256")
        != identity["holdout_identity_sha256"]
        or report.get("experiment_protocol_sha256")
        != protocol["experiment_protocol_sha256"]
        or report.get("candidate0_action_first") is not True
        or report.get("candidate0_pool_evidence_post_action") is not True
        or report.get("same_forward_claimed_for_supplementary_pool") is not False
        or report.get("real_native_callback_executed") is not True
        or report.get("fixed_dp_forward_executed_on_nonfresh_fixture")
        is not True
        or report.get("fresh_b3_opened") is not False
        or report.get("outcome_fields_consumed") != []
    ):
        raise ValueError("Fresh B3 production preflight report drifted")
    result = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_fresh_b3_production_preflight_review",
        "reviewed_root_sha256": source_root_sha256,
        "reviewed_manifest_paths": sorted(actual_paths),
        "holdout_identity_sha256": identity["holdout_identity_sha256"],
        "experiment_protocol_sha256": protocol["experiment_protocol_sha256"],
        "native_composition_review": independent,
        "paired_unit_count": 1,
        "arm_run_count": 3,
        "tick_count": 192,
        "fresh_b3_opened": False,
        "outcome_fields_consumed": [],
    }
    output.mkdir(parents=True)
    (output / "report.json").write_bytes(canonical_json_bytes(result))
    (output / "HEADS").write_bytes(
        (
            f"camp_head={_git_head()}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (output / "COMMAND").write_bytes(
        (" ".join(sys.argv) + "\n").encode("utf-8")
    )
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(
        output, label="independent V25 Fresh B3 production preflight review"
    )


def _review_actual_native_composition(
    *,
    payload: dict[str, Any],
    configs: dict[str, dict[str, Any]],
    primary: dict[str, dict[str, Any]],
    diagnostic: dict[str, Any],
    decision_evidence: dict[str, Any],
) -> None:
    diagnostic_ticks = _ticks(diagnostic, "candidate0 supplementary")
    for arm in ("candidate0", "static14d", "scene14d"):
        ticks = _ticks(primary[arm], arm)
        config = configs[arm]
        _review_decision_evidence(
            arm=arm,
            config=config,
            ticks=ticks,
            evidence=decision_evidence[arm],
        )
        model_sha = canonical_sha256(
            {
                "fixed_dp_head": config["fixed_dp"]["head"],
                "checkpoint_sha256": config["fixed_dp"]["checkpoint"][
                    "sha256"
                ],
                "args_sha256": config["fixed_dp"]["args_json"]["sha256"],
                "model_registry_sha256": config[
                    "runtime_selector_authority"
                ]["model_registry_sha256"],
            }
        )
        rows = payload["native_callback_receipts"][arm]
        if len(rows) != 64:
            raise ValueError(f"{arm} reviewed callback denominator drifted")
        for tick_index, (tick, row) in enumerate(zip(ticks, rows)):
            if tick.get("tick_index") != tick_index:
                raise ValueError(f"{arm} native tick order drifted")
            action_sha = tick.get("selected_trajectory_sha256")
            if row.get("input_sha256") != tick.get("input_sha256"):
                raise ValueError(f"{arm} input projection drifted")
            if (
                row.get("model_sha256") != model_sha
                or row.get("action_sha256") != action_sha
                or row.get("selected_action_sha256") != action_sha
            ):
                raise ValueError(f"{arm} model/action projection drifted")
            if arm == "candidate0":
                extra = diagnostic_ticks[tick_index]
                if (
                    tick.get("candidate0_action_first") is not True
                    or tick.get("same_forward_claimed") is not False
                    or extra.get("input_sha256") != tick.get("input_sha256")
                    or extra.get("default_output_sha256")
                    != tick.get("default_output_sha256")
                    or extra.get("selected_trajectory_sha256") != action_sha
                    or row.get("candidate_pool_sha256")
                    != extra.get("candidate_tensor_sha256_before")
                    or row.get("candidate0_pool_evidence_composed") is not True
                ):
                    raise ValueError(
                        "candidate0 action-first/supplementary projection drifted"
                    )
            elif (
                row.get("candidate_pool_sha256")
                != tick.get("candidate_tensor_sha256_before")
                or row.get("candidate0_pool_evidence_composed") is not False
            ):
                raise ValueError(f"{arm} candidate pool projection drifted")
            forward = validate_forward_binding(row["forward_binding"])
            if (
                forward["input_sha256"] != row["input_sha256"]
                or forward["model_sha256"] != model_sha
                or forward["action_sha256"] != action_sha
                or forward["candidate_pool_sha256"]
                != row["candidate_pool_sha256"]
            ):
                raise ValueError(f"{arm} forward binding drifted")
            latency = validate_latency_namespaces(row["latency_namespaces"])
            if arm == "candidate0":
                expected_latency = _independent_candidate0_latency(
                    tick, diagnostic_ticks[tick_index]
                )
            else:
                expected_latency = _independent_camp_latency(arm, tick)
            if not strict_equal(latency, expected_latency):
                raise ValueError(f"{arm} native latency projection drifted")
            online = latency["online_operational_latency_ms"]
            supplementary = latency["supplementary_evidence_latency_ms"]
            if arm == "candidate0":
                if (
                    any(
                        online[name] != 0.0
                        for name in (
                            "additional_k8_generation",
                            "atoms",
                            "context",
                            "scene_weight",
                            "selector",
                        )
                    )
                    or supplementary["candidate_pool_generation"] <= 0.0
                    or supplementary["atoms"] <= 0.0
                    or latency["supplementary_started_timestamp_ns"]
                    <= latency["action_available_timestamp_ns"]
                ):
                    raise ValueError(
                        "candidate0 latency namespace projection drifted"
                    )
            elif arm == "static14d":
                if (
                    online["context"] != 0.0
                    or online["scene_weight"] != 0.0
                    or any(value != 0.0 for value in supplementary.values())
                ):
                    raise ValueError("Static14D latency matrix drifted")
            elif (
                online["context"] <= 0.0
                or online["scene_weight"] <= 0.0
                or any(value != 0.0 for value in supplementary.values())
            ):
                raise ValueError("Scene14D latency matrix drifted")


def _independent_candidate0_latency(
    primary: dict[str, Any], diagnostic: dict[str, Any]
) -> dict[str, Any]:
    primary_latency = _native_latency(primary, "candidate0 primary")
    diagnostic_latency = _native_latency(
        diagnostic, "candidate0 supplementary"
    )
    online_total = _finite_nonnegative_latency(
        primary_latency, "hook_total"
    )
    diagnostic_hook = _finite_nonnegative_latency(
        diagnostic_latency, "hook_total"
    )
    diagnostic_atoms = _finite_nonnegative_latency(
        diagnostic_latency, "atom_materialization"
    )
    candidate_pool = diagnostic_hook - diagnostic_atoms
    runtime_total = _finite_nonnegative_latency(
        primary_latency, "total_planning"
    ) + _finite_nonnegative_latency(diagnostic_latency, "total_planning")
    overhead = runtime_total - online_total - diagnostic_hook
    if candidate_pool < 0.0 or overhead < 0.0:
        raise ValueError("candidate0 native latency decomposition drifted")
    return _freeze_independent_latency(
        arm="candidate0",
        online={
            "dp_operational_default": online_total,
            "additional_k8_generation": 0.0,
            "atoms": 0.0,
            "context": 0.0,
            "scene_weight": 0.0,
            "selector": 0.0,
        },
        supplementary={
            "candidate_pool_generation": candidate_pool,
            "atoms": diagnostic_atoms,
            "context": 0.0,
            "scene_weight": 0.0,
            "receipt_hashing": 0.0,
        },
        runtime_total=runtime_total,
        overhead=overhead,
        action_timestamp=_native_timestamp(
            primary, "action_available_ns"
        ),
        supplementary_timestamp=_native_timestamp(
            diagnostic, "planning_started_ns"
        ),
    )


def _independent_camp_latency(
    arm: str, tick: dict[str, Any]
) -> dict[str, Any]:
    latency = _native_latency(tick, arm)
    hook_total = _finite_nonnegative_latency(latency, "hook_total")
    components = {
        "additional_k8_generation": _finite_nonnegative_latency(
            latency, "candidate_inference"
        ),
        "atoms": _finite_nonnegative_latency(
            latency, "atom_materialization"
        ),
        "context": (
            _finite_nonnegative_latency(latency, "context")
            if arm == "scene14d"
            else 0.0
        ),
        "scene_weight": (
            _finite_nonnegative_latency(latency, "scene_weight")
            if arm == "scene14d"
            else 0.0
        ),
        "selector": _finite_nonnegative_latency(latency, "selector"),
    }
    dp_default = hook_total - sum(components.values())
    runtime_total = _finite_nonnegative_latency(latency, "total_planning")
    overhead = runtime_total - hook_total
    if dp_default < 0.0 or overhead < 0.0:
        raise ValueError(f"{arm} native latency decomposition drifted")
    return _freeze_independent_latency(
        arm=arm,
        online={
            "dp_operational_default": dp_default,
            **components,
        },
        supplementary={
            "candidate_pool_generation": 0.0,
            "atoms": 0.0,
            "context": 0.0,
            "scene_weight": 0.0,
            "receipt_hashing": 0.0,
        },
        runtime_total=runtime_total,
        overhead=overhead,
        action_timestamp=_native_timestamp(tick, "action_available_ns"),
        supplementary_timestamp=_native_timestamp(
            tick, "receipt_projected_ns"
        ),
    )


def _freeze_independent_latency(
    *,
    arm: str,
    online: dict[str, float],
    supplementary: dict[str, float],
    runtime_total: float,
    overhead: float,
    action_timestamp: int,
    supplementary_timestamp: int,
) -> dict[str, Any]:
    component_sum = float(
        sum(online.values()) + sum(supplementary.values()) + overhead
    )
    return {
        "schema_version": "camp_dp_v25_holdout_latency_namespaces_v1",
        "arm": arm,
        "online_operational_latency_ms": online,
        "supplementary_evidence_latency_ms": supplementary,
        "runtime_total_observed_ms": runtime_total,
        "runtime_nondecision_overhead_ms": overhead,
        "action_available_timestamp_ns": action_timestamp,
        "supplementary_started_timestamp_ns": supplementary_timestamp,
        "namespace_component_sum_ms": component_sum,
        "total_reconciliation_residual_ms": float(
            runtime_total - component_sum
        ),
        "fields_double_counted": [],
    }


def _native_latency(tick: dict[str, Any], label: str) -> dict[str, Any]:
    value = tick.get("latency_ms")
    if type(value) is not dict:
        raise ValueError(f"{label} native latency is missing")
    return value


def _finite_nonnegative_latency(
    value: dict[str, Any], field: str
) -> float:
    raw = value.get(field)
    if type(raw) not in {int, float} or type(raw) is bool:
        raise ValueError(f"native latency {field} type drifted")
    result = float(raw)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"native latency {field} value drifted")
    return result


def _native_timestamp(tick: dict[str, Any], field: str) -> int:
    value = tick.get(field)
    if type(value) is not int or value < 0:
        raise ValueError(f"native timestamp {field} drifted")
    return value


def _review_decision_evidence(
    *,
    arm: str,
    config: dict[str, Any],
    ticks: list[dict[str, Any]],
    evidence: Any,
) -> None:
    if type(evidence) is not list:
        raise ValueError(f"{arm} decision evidence must be a native list")
    if arm == "candidate0":
        if evidence != []:
            raise ValueError("candidate0 primary action carried CAMP evidence")
        return
    sample_every = config["protocol"].get("sample_every_ticks", 5)
    expected_indices = list(range(0, 64, sample_every))
    if len(evidence) != len(expected_indices):
        raise ValueError(f"{arm} decision evidence denominator drifted")
    for snapshot, tick_index in zip(
        evidence, expected_indices, strict=True
    ):
        if type(snapshot) is not dict:
            raise ValueError(f"{arm} decision snapshot type drifted")
        sidecar = snapshot.get("sidecar")
        if type(sidecar) is not dict:
            raise ValueError(f"{arm} decision snapshot sidecar is missing")
        native = ticks[tick_index]
        exact = {
            "tick_index": tick_index,
            "default_output_sha256": native["default_output_sha256"],
            "candidate_tensor_sha256_before": native[
                "candidate_tensor_sha256_before"
            ],
            "candidate_tensor_sha256_after": native[
                "candidate_tensor_sha256_after"
            ],
            "selected_index": native["selected_index"],
            "selected_trajectory_sha256": native[
                "selected_trajectory_sha256"
            ],
            "causal_input_sha256": native["input_sha256"],
        }
        if any(sidecar.get(name) != expected for name, expected in exact.items()):
            raise ValueError(
                f"{arm} decision snapshot/native receipt drifted"
            )


def _ticks(receipt: dict[str, Any], label: str) -> list[dict[str, Any]]:
    if (
        receipt.get("status") != "ok"
        or receipt.get("fixed_dp_head") != FIXED_DP_HEAD
        or type(receipt.get("ticks")) is not list
        or len(receipt["ticks"]) != 64
    ):
        raise ValueError(f"{label} native receipt drifted")
    return [dict(row) for row in receipt["ticks"]]


def _canonical_object(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    value = json.loads(
        raw.decode("utf-8", "strict"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {path}: {token}")
        ),
    )
    if type(value) is not dict or raw != canonical_json_bytes(value):
        raise ValueError(f"authority JSON is not canonical: {path}")
    return value


def _canonical_value(path: Path) -> Any:
    raw = path.read_bytes()
    value = _parse_json(raw, path)
    if raw != canonical_json_bytes(value):
        raise ValueError(f"authority JSON is not canonical: {path}")
    return value


def _parse_json(raw: bytes, path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    return json.loads(
        raw.decode("utf-8", "strict"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {path}: {token}")
        ),
    )


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-artifact", type=Path, required=True)
    parser.add_argument("--source-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = review(
        source_artifact=args.source_artifact,
        source_root_sha256=args.source_root_sha256,
        output_dir=args.output_dir,
    )
    print(root)


if __name__ == "__main__":
    main()
