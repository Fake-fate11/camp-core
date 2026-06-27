#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "dp_camp_v13_default_off_shadow_selector_runtime_manifest_materializer_v1"
DISABLED_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_default_off_disabled"
)
READY_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materialized"
)
REJECT_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer_rejected"
)
SOURCE_PLAN_SCHEMA_VERSION = (
    "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_v1"
)
RUNTIME_MANIFEST_SCHEMA_VERSION = "dp_camp_v13_default_off_shadow_selector_runtime_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
ATOM_SCHEMA_VERSION = "dp_camp_v10_14d"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_CANDIDATE_COUNT = 8
EXPECTED_ATOM_COUNT = 14

BLOCKED_AUTHORIZATIONS = (
    "default_off_shadow_selector_runtime_execution_authorized",
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
    "production_selector_change_authorized",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Default-off runtime artifact manifest materializer for the v13 "
            "CAMP shadow selector. It writes one immutable JSON manifest for "
            "existing fixed-DP-candidate reranking artifacts only when the "
            "explicit enable flag is present and all fail-closed checks pass."
        )
    )
    parser.add_argument("--artifact_manifest_materialization_plan_json", type=Path, required=True)
    parser.add_argument("--expected_materialization_plan_sha256", required=True)
    parser.add_argument("--output_runtime_manifest_json", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--enable_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_runtime_manifest(
        artifact_manifest_materialization_plan_json=args.artifact_manifest_materialization_plan_json,
        expected_materialization_plan_sha256=args.expected_materialization_plan_sha256,
        output_runtime_manifest_json=args.output_runtime_manifest_json,
        current_camp_head=args.current_camp_head,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        label=args.label,
        enabled=(
            args.enable_v13_default_off_shadow_selector_runtime_artifact_manifest_materializer
        ),
    )
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 1 if report["final_decision"]["status"] == REJECT_STATUS else 0


def build_runtime_manifest(
    *,
    artifact_manifest_materialization_plan_json: Path,
    expected_materialization_plan_sha256: str,
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
        artifact_manifest_materialization_plan_json=artifact_manifest_materialization_plan_json,
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
            "expected_materialization_plan_sha256_valid",
            _is_sha256(expected_materialization_plan_sha256),
            expected_materialization_plan_sha256,
            "sha256",
        ),
        _check(
            "materialization_plan_exists",
            artifact_manifest_materialization_plan_json.is_file(),
            str(artifact_manifest_materialization_plan_json),
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

    plan_payload: dict[str, Any] = {}
    plan_sha: str | None = None
    if artifact_manifest_materialization_plan_json.is_file():
        plan_sha = _sha256(artifact_manifest_materialization_plan_json)
        report["source_hashes"]["materialization_plan_sha256"] = plan_sha
        checks.append(
            _expect(
                "materialization_plan_sha256_matches_expected",
                plan_sha,
                expected_materialization_plan_sha256.lower(),
            )
        )
        loaded, json_check = _load_json(
            artifact_manifest_materialization_plan_json,
            "materialization_plan",
        )
        checks.append(json_check)
        plan_payload = _dict(loaded)

    checks.extend(_source_plan_checks(plan_payload, output_runtime_manifest_json))
    manifest = _build_manifest(
        plan_payload=plan_payload,
        materialization_plan_sha256=plan_sha,
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
        label=label,
    )
    checks.extend(_artifact_checks(manifest))

    passed = all(check["passed"] for check in checks)
    report["checks"] = checks
    report["runtime_manifest_preview"] = manifest if passed else {}
    if passed:
        output_runtime_manifest_json.parent.mkdir(parents=True, exist_ok=True)
        output_runtime_manifest_json.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
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
    artifact_manifest_materialization_plan_json: Path,
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
            "artifact_manifest_materialization_plan": str(
                artifact_manifest_materialization_plan_json
            ),
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
            "default_off_shadow_selector_runtime_execution_authorized": False,
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
            "production_selector_change_authorized": False,
            "training_executed": False,
            "failed_checks": [],
        },
    }


def _source_plan_checks(
    payload: dict[str, Any],
    output_runtime_manifest_json: Path,
) -> list[dict[str, Any]]:
    decision = _dict(payload.get("final_decision"))
    plan = _dict(payload.get("materialization_plan"))
    future = _dict(plan.get("future_manifest_required_content"))
    artifacts = _dict(future.get("artifacts"))
    atom_entry = _dict(artifacts.get("atom_scales"))
    weights_entry = _dict(artifacts.get("static_weights"))
    aliases = _dict(future.get("sha256"))
    return [
        _expect("source_plan_schema_version", payload.get("schema_version"), SOURCE_PLAN_SCHEMA_VERSION),
        _expect(
            "source_plan_status_ready",
            decision.get("status"),
            "dp_camp_v13_default_off_shadow_selector_artifact_manifest_materialization_plan_ready",
        ),
        _expect("source_plan_passed", decision.get("passed"), True),
        _expect("source_plan_failed_checks_empty", decision.get("failed_checks"), []),
        _expect("source_plan_not_runtime_manifest", plan.get("this_plan_is_runtime_manifest"), False),
        _expect("source_plan_runtime_manifest_not_written", plan.get("runtime_manifest_written_by_this_gate"), False),
        _expect("source_plan_runtime_not_enabled", plan.get("runtime_execution_enabled_by_this_gate"), False),
        _expect(
            "output_path_matches_source_plan",
            str(output_runtime_manifest_json),
            plan.get("planned_runtime_manifest_path"),
        ),
        _expect("future_manifest_schema", future.get("schema_version"), RUNTIME_MANIFEST_SCHEMA_VERSION),
        _expect("future_manifest_default_off", future.get("default_off"), True),
        _expect("future_manifest_selection_effect_false", future.get("selection_effect"), False),
        _expect("future_manifest_selector_mode_static", future.get("selector_mode"), "static"),
        _expect("future_manifest_candidate_operation", future.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("future_manifest_executed_policy", future.get("executed_output_policy"), "dp_top1"),
        _expect("future_manifest_candidate_count", future.get("required_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("future_manifest_atom_count", future.get("atom_count"), EXPECTED_ATOM_COUNT),
        _expect("future_manifest_atom_schema", future.get("atom_schema_version"), ATOM_SCHEMA_VERSION),
        _expect("future_manifest_score_expression", future.get("score_expression"), SCORE_EXPRESSION),
        _expect("future_manifest_required_dp_head", future.get("required_dp_head"), FIXED_DP_HEAD),
        _expect("future_manifest_atom_entry_logical_name", atom_entry.get("logical_name"), "atom_scales"),
        _check("future_manifest_atom_entry_path_present", bool(atom_entry.get("path")), atom_entry.get("path"), "nonempty path"),
        _check("future_manifest_atom_entry_sha256", _is_sha256(atom_entry.get("sha256")), atom_entry.get("sha256"), "sha256"),
        _expect("future_manifest_static_weights_logical_name", weights_entry.get("logical_name"), "static_weights"),
        _check("future_manifest_static_weights_path_present", bool(weights_entry.get("path")), weights_entry.get("path"), "nonempty path"),
        _check("future_manifest_static_weights_sha256", _is_sha256(weights_entry.get("sha256")), weights_entry.get("sha256"), "sha256"),
        _expect("future_manifest_alias_atom_scales", aliases.get("atom_scales"), atom_entry.get("sha256")),
        _expect("future_manifest_alias_static_weights", aliases.get("static_weights"), weights_entry.get("sha256")),
        *[
            _expect(f"source_plan_{name}_false", decision.get(name), False)
            for name in BLOCKED_AUTHORIZATIONS
        ],
    ]


def _build_manifest(
    *,
    plan_payload: dict[str, Any],
    materialization_plan_sha256: str | None,
    current_camp_head: str,
    current_dp_head: str,
    label: str | None,
) -> dict[str, Any]:
    plan = _dict(plan_payload.get("materialization_plan"))
    future = _dict(plan.get("future_manifest_required_content"))
    source_artifacts = _dict(future.get("artifacts"))
    artifacts: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    for logical_name in ("atom_scales", "static_weights"):
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

    return {
        "schema_version": RUNTIME_MANIFEST_SCHEMA_VERSION,
        "manifest_role": "default_off_shadow_selector_runtime_artifact_manifest",
        "label": label,
        "default_off": True,
        "selection_effect": False,
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
        "materialization_plan_sha256": materialization_plan_sha256,
        "artifacts": artifacts,
        "sha256": hashes,
        "authorizations": {
            "default_off_shadow_selector_runtime_execution_authorized": False,
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
            "production_selector_change_authorized": False,
            "training_executed": False,
        },
    }


def _artifact_checks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = _dict(manifest.get("artifacts"))
    checks: list[dict[str, Any]] = []
    for logical_name in ("atom_scales", "static_weights"):
        entry = _dict(artifacts.get(logical_name))
        path = Path(str(entry.get("path", "")))
        expected = _normalize_sha256(entry.get("sha256"))
        checks.append(_check(f"{logical_name}_path_exists", path.is_file(), str(path), "existing file"))
        checks.append(_check(f"{logical_name}_expected_sha256", expected is not None, expected, "sha256"))
        if path.is_file() and expected is not None:
            checks.append(
                _expect(f"{logical_name}_sha256_matches", _sha256(path), expected)
            )
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
        "production_selector_change_authorized": False,
        "training_executed": False,
        "failed_checks": failed,
    }


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
