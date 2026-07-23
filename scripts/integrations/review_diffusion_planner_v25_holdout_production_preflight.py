#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
    ARMS,
    canonical_json_bytes,
    canonical_sha256,
    freeze_fatal_artifact,
    freeze_forward_binding,
    freeze_latency_namespaces,
    freeze_unit_terminal,
    strict_equal,
    validate_experiment_protocol,
    validate_fatal_artifact,
    validate_holdout_identity,
    validate_unit_terminal,
)
from camp_core.integrations.diffusion_planner_v25_holdout_execution import (
    validate_holdout_arm_config,
)
from camp_core.integrations.diffusion_planner_v25_holdout_preflight import (
    CALLBACK_FIELDS,
    CALLBACK_SCHEMA_VERSION,
    PLAN_ARM_BY_ARM,
    PREFLIGHT_FIELDS,
    SCHEMA_VERSION,
    TICKS_PER_ARM,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
    FIXED_DP_HEAD,
)


def review_artifact(
    *,
    source_artifact: Path,
    source_root_sha256: str,
    output_dir: Path,
) -> str:
    source = Path(source_artifact).resolve()
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(output)
    seal = verify_complete_seal(
        source,
        source_root_sha256,
        label="V25 holdout production-composition preflight",
    )
    if (source / "run.exit").read_bytes() != b"0\n":
        raise ValueError("production preflight did not exit successfully")
    payload_files = {
        path.relative_to(source).as_posix()
        for path in source.rglob("*")
        if path.is_file()
        and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}
    }
    if payload_files != {"COMMAND", "HEADS", "preflight.json", "run.exit"}:
        raise ValueError("production preflight payload inventory drifted")
    payload = _canonical_object(source / "preflight.json")
    report = _independent_review(payload, source_root_sha256=seal["root_sha256"])
    output.mkdir(parents=True)
    (output / "report.json").write_bytes(canonical_json_bytes(report))
    (output / "HEADS").write_bytes(
        (
            f"camp_head={_git_head(ROOT)}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (output / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(
        output, label="independent V25 production-composition preflight review"
    )


def _independent_review(
    value: Mapping[str, Any], *, source_root_sha256: str
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != PREFLIGHT_FIELDS:
        raise ValueError("production preflight field set drifted")
    identity = validate_holdout_identity(value["holdout_identity"])
    protocol = validate_experiment_protocol(value["experiment_protocol"])
    configs = value["config_payloads"]
    if type(configs) is not dict or set(configs) != set(ARMS):
        raise ValueError("production preflight config arm set drifted")
    config_hashes: dict[str, str] = {}
    callback_hashes: dict[str, str] = {}
    for arm in ARMS:
        config = validate_holdout_arm_config(configs[arm])
        if (
            config["holdout_authority"]["holdout_identity_sha256"]
            != identity["holdout_identity_sha256"]
            or config["holdout_authority"]["experiment_protocol_sha256"]
            != protocol["experiment_protocol_sha256"]
            or config["protocol"]["holdout_plan_arm"] != PLAN_ARM_BY_ARM[arm]
            or config["protocol"]["holdout_opening_arm"] != arm
            or config["protocol"]["candidate0_offline_pool_evidence_required"]
            is not (arm == "candidate0")
        ):
            raise ValueError("production preflight embedded config drifted")
        config_hashes[arm] = canonical_sha256(config)
        rows = value["native_callback_receipts"].get(arm)
        if type(rows) is not list or len(rows) != TICKS_PER_ARM:
            raise ValueError("production preflight callback denominator drifted")
        expected_rows = [
            _independent_callback(config, arm=arm, tick_index=tick_index)
            for tick_index in range(TICKS_PER_ARM)
        ]
        if not strict_equal(rows, expected_rows):
            raise ValueError("production preflight native callback receipt drifted")
        callback_hashes[arm] = canonical_sha256(rows)
        terminal = validate_unit_terminal(value["arm_terminals"].get(arm))
        if not strict_equal(
            terminal,
            freeze_unit_terminal(
                status="complete", failure_class=None, all_k_bad=False
            ),
        ):
            raise ValueError("production preflight arm terminal drifted")
    if not strict_equal(value["config_sha256"], config_hashes):
        raise ValueError("production preflight config SHA drifted")
    _independent_path_matrix(value["path_matrix"], identity, protocol)
    exact = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_exact_production_composition_preflight",
        "paired_unit_count": 1,
        "arm_run_count": 3,
        "tick_count": 192,
        "candidate0_offline_pool_evidence_required": True,
        "action_committed_before_supplementary_evidence": True,
        "fresh_opened": False,
        "outcome_fields_consumed": [],
    }
    for name, expected in exact.items():
        if not strict_equal(value.get(name), expected):
            raise ValueError(f"production preflight {name} drifted")
    payload = dict(value)
    stored = payload.pop("preflight_payload_sha256")
    if stored != canonical_sha256(payload):
        raise ValueError("production preflight payload SHA drifted")
    return {
        "schema_version": (
            "camp_dp_v25_holdout_production_composition_preflight_review_v1"
        ),
        "status": "passed_independent_production_composition_preflight_review",
        "reviewed_root_sha256": source_root_sha256,
        "holdout_identity_sha256": identity["holdout_identity_sha256"],
        "experiment_protocol_sha256": protocol["experiment_protocol_sha256"],
        "config_sha256": config_hashes,
        "callback_receipt_sha256": callback_hashes,
        "paired_unit_count": 1,
        "arm_run_count": 3,
        "tick_count": 192,
        "success_path_reviewed": True,
        "typed_scientific_failure_path_reviewed": True,
        "artifact_fatal_path_reviewed": True,
        "fresh_opened": False,
        "outcome_fields_consumed": [],
    }


def _independent_callback(
    config: Mapping[str, Any], *, arm: str, tick_index: int
) -> dict[str, Any]:
    config_sha = canonical_sha256(config)
    input_sha = _digest(config_sha, arm, tick_index, "input")
    model_sha = _digest(
        config["fixed_dp"]["checkpoint"]["sha256"],
        config["runtime_selector_authority"]["model_registry_sha256"],
        arm,
        "model",
    )
    action_sha = _digest(input_sha, model_sha, arm, tick_index, "action")
    pool_sha = _digest(input_sha, model_sha, tick_index, "candidate-pool")
    online = {
        "dp_operational_default": 1.0,
        "additional_k8_generation": 0.0,
        "atoms": 0.0,
        "context": 0.0,
        "scene_weight": 0.0,
        "selector": 0.0,
    }
    supplementary = {
        "candidate_pool_generation": 0.0,
        "atoms": 0.0,
        "context": 0.0,
        "scene_weight": 0.0,
        "receipt_hashing": 0.1,
    }
    if arm == "candidate0":
        supplementary["candidate_pool_generation"] = 7.0
        supplementary["atoms"] = 0.3
    else:
        online["additional_k8_generation"] = 7.0
        online["atoms"] = 0.3
        online["selector"] = 0.1
    if arm == "scene14d":
        online["context"] = 0.2
        online["scene_weight"] = 0.05
    overhead = 0.5
    total = sum(online.values()) + sum(supplementary.values()) + overhead
    action_timestamp = 1_000_000 + tick_index * 10
    result = {
        "schema_version": CALLBACK_SCHEMA_VERSION,
        "arm": arm,
        "tick_index": tick_index,
        "input_sha256": input_sha,
        "model_sha256": model_sha,
        "action_sha256": action_sha,
        "candidate_pool_sha256": pool_sha,
        "forward_binding": freeze_forward_binding(
            tick_index=tick_index,
            input_sha256=input_sha,
            model_sha256=model_sha,
            action_sha256=action_sha,
            candidate_pool_sha256=pool_sha,
        ),
        "latency_namespaces": freeze_latency_namespaces(
            arm=arm,
            online_operational_latency_ms=online,
            supplementary_evidence_latency_ms=supplementary,
            runtime_total_observed_ms=total,
            runtime_nondecision_overhead_ms=overhead,
            action_available_timestamp_ns=action_timestamp,
            supplementary_started_timestamp_ns=action_timestamp + 1,
        ),
        "candidate0_pool_evidence_composed": arm == "candidate0",
        "receipt_projection_completed": True,
        "action_committed_before_supplementary_evidence": True,
        "selected_action_sha256": action_sha,
    }
    if set(result) != CALLBACK_FIELDS:
        raise AssertionError("independent callback oracle field set drifted")
    return result


def _independent_path_matrix(
    value: Mapping[str, Any],
    identity: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> None:
    common = {
        "block_class": "synthetic_preflight_crash_injection",
        "controller_decision_root_sha256": "1" * 64,
        "opening_release_root_sha256": "2" * 64,
        "holdout_identity_sha256": identity["holdout_identity_sha256"],
        "experiment_protocol_sha256": protocol["experiment_protocol_sha256"],
        "planned_arm_run_count": 3,
        "outcome_fields_consumed": [],
    }
    marker_path = (
        "/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas/"
        "synthetic-preflight-marker.json"
    )
    expected = {
        "success": freeze_unit_terminal(
            status="complete", failure_class=None, all_k_bad=False
        ),
        "typed_scientific_failure": freeze_unit_terminal(
            status="fixed_dp_candidate_generation_capability_failure",
            failure_class="invalid_k8_heading_norm_envelope",
            all_k_bad=False,
        ),
        "artifact_fatal": {
            "before_nonce": freeze_fatal_artifact(
                reason="before_nonce_consumption",
                marker_path=None,
                marker_sha256=None,
                attempted_unit_ordinal=None,
                attempted_arm=None,
                attempted_arm_run_count=0,
                complete_arm_run_count=0,
                fresh_opened_once=False,
                **common,
            ),
            "after_marker_before_run": freeze_fatal_artifact(
                reason="after_marker_before_run",
                marker_path=marker_path,
                marker_sha256="3" * 64,
                attempted_unit_ordinal=None,
                attempted_arm=None,
                attempted_arm_run_count=0,
                complete_arm_run_count=0,
                fresh_opened_once=True,
                **common,
            ),
            "after_run_before_receipt": freeze_fatal_artifact(
                reason="after_run_before_receipt",
                marker_path=marker_path,
                marker_sha256="3" * 64,
                attempted_unit_ordinal=0,
                attempted_arm="candidate0",
                attempted_arm_run_count=1,
                complete_arm_run_count=0,
                fresh_opened_once=True,
                **common,
            ),
            "after_receipt_before_seal": freeze_fatal_artifact(
                reason="after_receipt_before_seal",
                marker_path=marker_path,
                marker_sha256="3" * 64,
                attempted_unit_ordinal=0,
                attempted_arm="candidate0",
                attempted_arm_run_count=1,
                complete_arm_run_count=1,
                fresh_opened_once=True,
                **common,
            ),
        },
    }
    if not strict_equal(value, expected):
        raise ValueError("production preflight path matrix drifted")
    for row in value["artifact_fatal"].values():
        validate_fatal_artifact(row)


def _canonical_object(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {path}: {token}")
        ),
    )
    if type(value) is not dict or raw != canonical_json_bytes(value):
        raise ValueError(f"authority JSON is not canonical: {path}")
    return value


def _digest(*values: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(list(values))).hexdigest()


def _git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-artifact", type=Path, required=True)
    parser.add_argument("--source-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    root = review_artifact(
        source_artifact=args.source_artifact,
        source_root_sha256=args.source_root_sha256,
        output_dir=args.output_dir,
    )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
