#!/usr/bin/env python3
"""Materialize the v14 default-off shadow selector runtime artifact manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "runtime_artifact_manifest_materializer_v1"
)
SOURCE_PLAN_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_implementation_plan_v1"
)
RUNTIME_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1"
)
DISABLED_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materializer_default_off_disabled"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialized"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materializer_rejected"
)
SOURCE_PLAN_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materialization_implementation_plan_ready"
)
IMPLEMENTATION_COMPLETE_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materializer_implementation_complete"
)
POST_IMPLEMENTATION_STATIC_REVIEW_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
    "shadow_replay_evaluation_default_off_shadow_selector_"
    "runtime_artifact_manifest_materializer_post_implementation_static_contract_review_only"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_SCOPE = "public_simulator_fixed_dp_candidate_tensor"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
ATOM_SCHEMA_VERSION = "camp_legacy_v1_9d"
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 9
RUNTIME_ENTRIES = ("atom_scales", "static_weights")

BLOCKED_AUTHORIZATIONS = (
    "default_off_shadow_selector_runtime_execution_authorized",
    "runtime_artifact_manifest_materialization_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployment_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "replay_execution_authorized",
    "candidate_generation_authorized",
    "dp_modification_authorized",
    "online_selector_change_authorized",
    "executed_trajectory_change_authorized",
    "training_authorized",
    "training_execution_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Default-off v14 runtime artifact manifest materializer for CAMP "
            "shadow reranking of fixed Diffusion Planner candidate tensors."
        )
    )
    parser.add_argument(
        "--runtime_artifact_manifest_materialization_implementation_plan_json",
        type=Path,
        required=True,
    )
    parser.add_argument("--expected_implementation_plan_sha256", required=True)
    parser.add_argument("--output_runtime_manifest_json", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_runtime_manifest(
        runtime_artifact_manifest_materialization_implementation_plan_json=(
            args.runtime_artifact_manifest_materialization_implementation_plan_json
        ),
        expected_implementation_plan_sha256=args.expected_implementation_plan_sha256,
        output_runtime_manifest_json=args.output_runtime_manifest_json,
        current_camp_head=args.current_camp_head,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer
        ),
    )
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 1 if report["final_decision"]["status"] == REJECT_STATUS else 0


def build_runtime_manifest(
    *,
    runtime_artifact_manifest_materialization_implementation_plan_json: Path,
    expected_implementation_plan_sha256: str,
    output_runtime_manifest_json: Path,
    current_camp_head: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    label: str | None = None,
    enabled: bool = False,
) -> dict[str, Any]:
    report = _empty_report(
        enabled=enabled,
        label=label,
        source_plan_json=runtime_artifact_manifest_materialization_implementation_plan_json,
        output_runtime_manifest_json=output_runtime_manifest_json,
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
    )
    if not enabled:
        return report

    checks: list[dict[str, Any]] = [
        _check(
            "current_camp_head_is_sha",
            _is_git_sha(current_camp_head),
            current_camp_head,
            "40-char git sha",
        ),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check(
            "expected_implementation_plan_sha256_valid",
            _is_sha256(expected_implementation_plan_sha256),
            expected_implementation_plan_sha256,
            "sha256",
        ),
        _check(
            "source_implementation_plan_exists",
            runtime_artifact_manifest_materialization_implementation_plan_json.is_file(),
            str(runtime_artifact_manifest_materialization_implementation_plan_json),
            "existing file",
        ),
        _check(
            "output_runtime_manifest_path_is_json",
            str(output_runtime_manifest_json).endswith(".json"),
            str(output_runtime_manifest_json),
            "*.json",
        ),
        _check(
            "output_runtime_manifest_absent_before_write",
            not output_runtime_manifest_json.exists(),
            str(output_runtime_manifest_json),
            "path does not exist",
        ),
    ]

    source_plan: dict[str, Any] = {}
    plan_sha: str | None = None
    if runtime_artifact_manifest_materialization_implementation_plan_json.is_file():
        plan_sha = _sha256(
            runtime_artifact_manifest_materialization_implementation_plan_json
        )
        report["source_hashes"]["implementation_plan_sha256"] = plan_sha
        checks.append(
            _expect(
                "implementation_plan_sha256_matches_expected",
                plan_sha,
                expected_implementation_plan_sha256.lower(),
            )
        )
        loaded, json_check = _load_json(
            runtime_artifact_manifest_materialization_implementation_plan_json,
            "implementation_plan",
        )
        checks.append(json_check)
        source_plan = _dict(loaded)

    checks.extend(_source_plan_checks(source_plan, output_runtime_manifest_json))
    manifest = _build_manifest(
        source_plan=source_plan,
        implementation_plan_sha256=plan_sha,
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
        label=label,
    )
    checks.extend(_runtime_manifest_contract_checks(manifest))
    checks.extend(_artifact_file_checks(manifest))

    passed = all(check["passed"] for check in checks)
    report["checks"] = checks
    report["runtime_manifest_preview"] = manifest if passed else {}
    if passed:
        _atomic_write_json(output_runtime_manifest_json, manifest)
        report["output_hashes"]["runtime_manifest_sha256"] = _sha256(
            output_runtime_manifest_json
        )
    report["final_decision"] = _decision(
        passed=passed,
        checks=checks,
        output_runtime_manifest_json=output_runtime_manifest_json,
    )
    return report


def _empty_report(
    *,
    enabled: bool,
    label: str | None,
    source_plan_json: Path,
    output_runtime_manifest_json: Path,
    current_camp_head: str,
    current_dp_head: str,
    required_dp_head: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "label": label,
            "default_off": True,
            "enabled": bool(enabled),
            "materializer_only": True,
            "source_implementation_plan_json": str(source_plan_json),
            "output_runtime_manifest_json": str(output_runtime_manifest_json),
            "current_camp_head": current_camp_head,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "dp_modification_execution": False,
            "replay_execution": False,
            "training_execution": False,
            "candidate_generation_execution": False,
            "real_runtime_manifest_materialized": False,
            "implementation_complete_status": IMPLEMENTATION_COMPLETE_STATUS,
            "authorized_next_work_after_implementation": (
                POST_IMPLEMENTATION_STATIC_REVIEW_WORK
            ),
        },
        "source_hashes": {},
        "output_hashes": {},
        "runtime_manifest_preview": {},
        "checks": [],
        "final_decision": {
            "status": DISABLED_STATUS,
            "passed": False,
            "enabled": False,
            "runtime_manifest_written": False,
            "output_runtime_manifest_json": None,
            "default_off_shadow_selector_runtime_execution_authorized": False,
            "runtime_artifact_manifest_materialization_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "executed_trajectory_change_authorized": False,
            "training_authorized": False,
            "training_execution_authorized": False,
            "training_executed": False,
            "failed_checks": [],
        },
    }


def _source_plan_checks(
    payload: dict[str, Any],
    output_runtime_manifest_json: Path,
) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("implementation_plan"))
    contract = _dict(plan.get("future_materializer_contract"))
    future = _dict(contract.get("manifest_required_content"))
    artifacts = _dict(future.get("artifacts"))
    aliases = _dict(future.get("sha256"))
    atom_entry = _dict(artifacts.get("atom_scales"))
    weights_entry = _dict(artifacts.get("static_weights"))
    claims = _dict(future.get("forbidden_runtime_claims"))
    checks = [
        _expect("source_plan_schema_version", payload.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect("source_plan_status_ready", decision.get("status"), SOURCE_PLAN_STATUS),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_plan_not_manifest_written", plan.get("runtime_manifest_written_by_this_gate"), False),
        _expect("source_plan_not_manifest_materialized", plan.get("runtime_manifest_materialized_by_this_gate"), False),
        _expect("source_plan_runtime_not_enabled", plan.get("runtime_execution_enabled_by_this_gate"), False),
        _expect("source_plan_write_strategy", contract.get("write_strategy"), "same-directory temp file plus atomic replace"),
        _expect("source_plan_writes_one_manifest", contract.get("writes_exactly_one_runtime_manifest"), True),
        _expect("output_path_matches_source_plan", str(output_runtime_manifest_json), contract.get("planned_output_path")),
        _expect("future_manifest_schema", future.get("schema_version"), RUNTIME_MANIFEST_SCHEMA_VERSION),
        _expect("future_manifest_role", future.get("manifest_role"), "default_off_shadow_selector_runtime_artifact_manifest"),
        _expect("future_manifest_source_scope", future.get("source_scope"), SOURCE_SCOPE),
        _expect("future_manifest_default_off", future.get("default_off"), True),
        _expect("future_manifest_fail_closed", future.get("fail_closed"), True),
        _expect("future_manifest_selection_effect_false", future.get("selection_effect"), False),
        _expect("future_manifest_online_selector_change_false", future.get("online_selector_change"), False),
        _expect("future_manifest_selector_mode_static", future.get("selector_mode"), "static"),
        _expect("future_manifest_candidate_operation", future.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("future_manifest_executed_policy", future.get("executed_output_policy"), "dp_top1"),
        _expect("future_manifest_candidate_count", future.get("required_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("future_manifest_atom_count", future.get("atom_count"), EXPECTED_ATOM_COUNT),
        _expect("future_manifest_atom_schema", future.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("future_manifest_score_expression", future.get("score_expression"), SCORE_EXPRESSION),
        _expect("future_manifest_required_dp_head", contract.get("required_dp_head"), FIXED_DP_HEAD),
        _expect("future_manifest_atom_entry_logical_name", atom_entry.get("logical_name"), "atom_scales"),
        _check("future_manifest_atom_entry_path_present", bool(atom_entry.get("path")), atom_entry.get("path"), "nonempty path"),
        _check("future_manifest_atom_entry_sha256", _is_sha256(atom_entry.get("sha256")), atom_entry.get("sha256"), "sha256"),
        _expect("future_manifest_static_weights_logical_name", weights_entry.get("logical_name"), "static_weights"),
        _check("future_manifest_static_weights_path_present", bool(weights_entry.get("path")), weights_entry.get("path"), "nonempty path"),
        _check("future_manifest_static_weights_sha256", _is_sha256(weights_entry.get("sha256")), weights_entry.get("sha256"), "sha256"),
        _expect("future_manifest_alias_atom_scales", aliases.get("atom_scales"), atom_entry.get("sha256")),
        _expect("future_manifest_alias_static_weights", aliases.get("static_weights"), weights_entry.get("sha256")),
        _expect("future_manifest_alias_atom_path", aliases.get(atom_entry.get("path")), atom_entry.get("sha256")),
        _expect("future_manifest_alias_weight_path", aliases.get(weights_entry.get("path")), weights_entry.get("sha256")),
        _expect("future_manifest_alias_atom_basename", aliases.get(Path(str(atom_entry.get("path"))).name), atom_entry.get("sha256")),
        _expect("future_manifest_alias_weight_basename", aliases.get(Path(str(weights_entry.get("path"))).name), weights_entry.get("sha256")),
    ]
    for name in BLOCKED_AUTHORIZATIONS:
        if name in decision:
            checks.append(_expect(f"source_plan_{name}_false", decision.get(name), False))
    for name in (
        "selector_promotion_authorized",
        "atom_promotion_authorized",
        "deployment_authorized",
        "safety_benefit_claim_authorized",
        "camp_over_dp_top1_claim_authorized",
    ):
        checks.append(_expect(f"future_manifest_{name}_false", claims.get(name), False))
    return checks


def _build_manifest(
    *,
    source_plan: dict[str, Any],
    implementation_plan_sha256: str | None,
    current_camp_head: str,
    current_dp_head: str,
    label: str | None,
) -> dict[str, Any]:
    plan = _dict(source_plan.get("implementation_plan"))
    contract = _dict(plan.get("future_materializer_contract"))
    future = _dict(contract.get("manifest_required_content"))
    source_artifacts = _dict(future.get("artifacts"))
    source_aliases = _dict(future.get("sha256"))
    artifacts: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    for logical_name in RUNTIME_ENTRIES:
        source_entry = _dict(source_artifacts.get(logical_name))
        path = Path(str(source_entry.get("path", "")))
        expected_sha = _normalize_sha256(source_entry.get("sha256"))
        artifacts[logical_name] = {
            "logical_name": logical_name,
            "path": str(path),
            "sha256": expected_sha,
            "required": True,
        }
        if expected_sha is not None:
            hashes[logical_name] = expected_sha
            hashes[path.name] = expected_sha
            hashes[str(path)] = expected_sha
    for key, value in source_aliases.items():
        normalized = _normalize_sha256(value)
        if normalized is not None:
            hashes[str(key)] = normalized

    return {
        "schema_version": RUNTIME_MANIFEST_SCHEMA_VERSION,
        "manifest_role": "default_off_shadow_selector_runtime_artifact_manifest",
        "label": label,
        "source_scope": SOURCE_SCOPE,
        "default_off": True,
        "fail_closed": True,
        "selection_effect": False,
        "online_selector_change": False,
        "selector_mode": "static",
        "candidate_operation": "fixed DP candidate reranking only",
        "executed_output_policy": "dp_top1",
        "required_candidate_count": EXPECTED_CANDIDATE_COUNT,
        "atom_count": EXPECTED_ATOM_COUNT,
        "atom_schema_version": ATOM_SCHEMA_VERSION,
        "score_expression": SCORE_EXPRESSION,
        "required_dp_head": FIXED_DP_HEAD,
        "current_dp_head": current_dp_head,
        "current_camp_head": current_camp_head,
        "implementation_plan_sha256": implementation_plan_sha256,
        "artifacts": artifacts,
        "sha256": hashes,
        "authorizations": {
            "default_off_shadow_selector_runtime_execution_authorized": False,
            "runtime_artifact_manifest_materialization_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "executed_trajectory_change_authorized": False,
            "training_authorized": False,
            "training_execution_authorized": False,
            "training_executed": False,
        },
    }


def _runtime_manifest_contract_checks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = _dict(manifest.get("artifacts"))
    hashes = _dict(manifest.get("sha256"))
    authorizations = _dict(manifest.get("authorizations"))
    checks = [
        _expect("manifest_schema", manifest.get("schema_version"), RUNTIME_MANIFEST_SCHEMA_VERSION),
        _expect("manifest_role", manifest.get("manifest_role"), "default_off_shadow_selector_runtime_artifact_manifest"),
        _expect("manifest_source_scope", manifest.get("source_scope"), SOURCE_SCOPE),
        _expect("manifest_default_off", manifest.get("default_off"), True),
        _expect("manifest_fail_closed", manifest.get("fail_closed"), True),
        _expect("manifest_selection_effect_false", manifest.get("selection_effect"), False),
        _expect("manifest_online_selector_change_false", manifest.get("online_selector_change"), False),
        _expect("manifest_selector_mode", manifest.get("selector_mode"), "static"),
        _expect("manifest_candidate_operation", manifest.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("manifest_executed_output_policy", manifest.get("executed_output_policy"), "dp_top1"),
        _expect("manifest_candidate_count", manifest.get("required_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("manifest_atom_count", manifest.get("atom_count"), EXPECTED_ATOM_COUNT),
        _expect("manifest_atom_schema", manifest.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("manifest_score_expression", manifest.get("score_expression"), SCORE_EXPRESSION),
        _expect("manifest_required_dp_head", manifest.get("required_dp_head"), FIXED_DP_HEAD),
        _expect("manifest_artifact_keys", sorted(artifacts), sorted(RUNTIME_ENTRIES)),
    ]
    for logical_name in RUNTIME_ENTRIES:
        entry = _dict(artifacts.get(logical_name))
        path = Path(str(entry.get("path", "")))
        expected = _normalize_sha256(entry.get("sha256"))
        checks.extend(
            [
                _expect(f"manifest_{logical_name}_logical_name", entry.get("logical_name"), logical_name),
                _check(f"manifest_{logical_name}_path_present", bool(entry.get("path")), entry.get("path"), "nonempty path"),
                _check(f"manifest_{logical_name}_sha256", expected is not None, expected, "sha256"),
                _expect(f"manifest_{logical_name}_required", entry.get("required"), True),
                _expect(f"manifest_{logical_name}_logical_alias", hashes.get(logical_name), expected),
                _expect(f"manifest_{logical_name}_basename_alias", hashes.get(path.name), expected),
                _expect(f"manifest_{logical_name}_path_alias", hashes.get(str(path)), expected),
            ]
        )
    for name in BLOCKED_AUTHORIZATIONS:
        checks.append(_expect(f"manifest_{name}_false", authorizations.get(name), False))
    checks.append(_expect("manifest_training_executed_false", authorizations.get("training_executed"), False))
    return checks


def _artifact_file_checks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = _dict(manifest.get("artifacts"))
    checks: list[dict[str, Any]] = []
    for logical_name in RUNTIME_ENTRIES:
        entry = _dict(artifacts.get(logical_name))
        path = Path(str(entry.get("path", "")))
        expected = _normalize_sha256(entry.get("sha256"))
        checks.append(_check(f"{logical_name}_path_exists", path.is_file(), str(path), "existing file"))
        checks.append(_check(f"{logical_name}_expected_sha256", expected is not None, expected, "sha256"))
        if path.is_file() and expected is not None:
            checks.append(_expect(f"{logical_name}_sha256_matches", _sha256(path), expected))
    return checks


def _decision(
    *,
    passed: bool,
    checks: list[dict[str, Any]],
    output_runtime_manifest_json: Path,
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "enabled": True,
        "runtime_manifest_written": bool(passed),
        "output_runtime_manifest_json": str(output_runtime_manifest_json) if passed else None,
        "default_off_shadow_selector_runtime_execution_authorized": False,
        "runtime_artifact_manifest_materialization_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "replay_execution_authorized": False,
        "candidate_generation_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "executed_trajectory_change_authorized": False,
        "training_authorized": False,
        "training_execution_authorized": False,
        "training_executed": False,
        "failed_checks": failed,
    }


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temp_path = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    try:
        with temp_path.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        _fsync_parent(path.parent)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _fsync_parent(parent: Path) -> None:
    if os.name == "nt":
        return
    flags = getattr(os, "O_RDONLY", 0)
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    try:
        fd = os.open(parent, flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _load_json(path: Path, name: str) -> tuple[Any, dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, _check(f"{name}_valid_json", False, type(exc).__name__, "valid JSON")
    return payload, _check(f"{name}_json_object", isinstance(payload, dict), type(payload).__name__, "dict")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_sha256(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if _is_sha256(text):
        return text
    return None


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": _stable(observed),
        "expected": _stable(expected),
    }


def _stable(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    return value


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        ch in "0123456789abcdef" for ch in value.lower()
    )


if __name__ == "__main__":
    raise SystemExit(main())
