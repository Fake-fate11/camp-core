#!/usr/bin/env python3
"""Materialize the v15 broader non-formal source inventory."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_review_module():
    path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_source_inventory_preflight_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location("v15_source_inventory_preflight_static_review", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


REVIEW_MODULE = _load_review_module()
PREFLIGHT_MODULE = REVIEW_MODULE.PREFLIGHT_MODULE
PLAN_MODULE = PREFLIGHT_MODULE.PLAN_MODULE

FIXED_DP_HEAD = REVIEW_MODULE.FIXED_DP_HEAD
SCHEMA_VERSION = "dp_camp_v15_broader_nonformal_evidence_expansion_source_inventory_execution_v1"
AUTHORIZED_CURRENT_WORK = REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v15_broader_nonformal_evidence_expansion_source_inventory_execution_passed"
REJECT_STATUS = "v15_broader_nonformal_evidence_expansion_source_inventory_execution_rejected"
AUTHORIZED_NEXT_WORK = "v15_broader_nonformal_evidence_expansion_source_inventory_execution_result_review_only"
INVENTORY_JSON_NAME = "source_inventory.json"
INVENTORY_MD_NAME = "source_inventory.md"
SPLIT_MANIFEST_NAME = "split_manifest.json"
ZERO_OVERLAP_PLAN_NAME = "zero_overlap_plan.json"
SCENARIO_BUCKET_MANIFEST_NAME = "scenario_bucket_manifest.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_md", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--v15_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v15_broader_nonformal_evidence_expansion_source_inventory_execution",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_static_review_md=args.source_static_review_md,
        source_static_review_sha256s=args.source_static_review_sha256s,
        v14_audit_md=args.v14_audit_md,
        v15_audit_md=args.v15_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v15_broader_nonformal_evidence_expansion_source_inventory_execution,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_static_review_artifact_dir: Path,
    source_static_review_json: Path,
    source_static_review_md: Path,
    source_static_review_sha256s: Path,
    v14_audit_md: Path,
    v15_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact = source_static_review_artifact_dir.resolve()
    source_review = _read_json(source_static_review_json)
    root_sha256s = _read_sha256s(source_static_review_sha256s)
    v14_text = v14_audit_md.read_text(encoding="utf-8")
    v15_text = v15_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    inventory = _inventory(current_camp_head, current_dp_head)
    split_manifest = _split_manifest()
    zero_overlap_plan = _zero_overlap_plan()
    scenario_manifest = _scenario_bucket_manifest()

    checks = [
        _expect("execution_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("source_static_review_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_static_review_schema", source_review.get("schema_version"), REVIEW_MODULE.SCHEMA_VERSION),
        _expect("source_static_review_passed", source_review["final_decision"].get("passed"), True),
        _expect("source_static_review_authorized_execution", source_review["final_decision"].get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_inventory_not_already_executed_by_review", source_review["final_decision"].get("inventory_executed"), False),
        _contains("audit_authorizes_execution", v15_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_execution", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("v14_sealed_auditable_complete", v14_text, "auditable_integration_complete=True"),
        _contains("v14_fixed_dp_scope", v14_text, "CAMP selector over fixed Diffusion Planner candidate tensor"),
        _expect("inventory_uses_fixed_dp_head", inventory["fixed_dp_head"], FIXED_DP_HEAD),
        _expect("inventory_full36_used", inventory["blocked_inputs"]["Full36"], False),
        _expect("inventory_formal_seeds_used", inventory["blocked_inputs"]["formal_seeds_11_12_13"], False),
        _expect("inventory_training_executed", inventory["executions"]["training"], False),
        _expect("inventory_paired_evaluation_executed", inventory["executions"]["paired_evaluation"], False),
        _expect("inventory_dp_modified", inventory["mutations"]["dp_modified"], False),
        _expect("inventory_candidate_tensor_modified", inventory["mutations"]["candidate_tensor_modified"], False),
        _expect("inventory_trajectory_modified", inventory["mutations"]["trajectory_modified"], False),
    ]
    for name in ("HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit", REVIEW_MODULE.REVIEW_JSON_NAME, REVIEW_MODULE.REVIEW_MD_NAME):
        checks.append(_check(f"source_artifact_has_{name}", (artifact / name).is_file(), str(artifact / name), "file"))
        if (artifact / name).is_file() and name in root_sha256s:
            checks.append(_expect(f"source_artifact_sha_{name}", _sha256(artifact / name), root_sha256s[name]))
    checks.extend(
        [
            _check("split_manifest_has_train_calibration_holdout", set(split_manifest) == {"train", "calibration", "holdout"}, split_manifest, "three splits"),
            _check("zero_overlap_keys_registered", len(zero_overlap_plan["zero_overlap_keys"]) >= 6, zero_overlap_plan["zero_overlap_keys"], ">=6 keys"),
            _check("scenario_buckets_registered", set(scenario_manifest["scenario_buckets"]) == set(PLAN_MODULE.SCENARIO_BUCKETS), scenario_manifest["scenario_buckets"], PLAN_MODULE.SCENARIO_BUCKETS),
        ]
    )

    failed = [check["name"] for check in checks if not check["passed"]]
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if not failed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK,
            "source_static_review_artifact": str(artifact),
            "inventory": inventory,
            "split_manifest": split_manifest,
            "zero_overlap_plan": zero_overlap_plan,
            "scenario_bucket_manifest": scenario_manifest,
            "checks": checks,
            "final_decision": {
                "passed": not failed,
                "status": READY_STATUS if not failed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
                "inventory_executed": True,
                "training_executed": False,
                "paired_evaluation_executed": False,
                "full36_used": False,
                "formal_seed_11_12_13_used": False,
                "dp_modified": False,
                "candidate_tensor_modified": False,
                "trajectory_modified": False,
            },
        }
    )


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        INVENTORY_JSON_NAME: report,
        SPLIT_MANIFEST_NAME: report["split_manifest"],
        ZERO_OVERLAP_PLAN_NAME: report["zero_overlap_plan"],
        SCENARIO_BUCKET_MANIFEST_NAME: report["scenario_bucket_manifest"],
    }
    for name, payload in files.items():
        (output_dir / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / INVENTORY_MD_NAME).write_text(_render_markdown(report), encoding="utf-8")
    sha_inputs = [output_dir / name for name in (*files.keys(), INVENTORY_MD_NAME)]
    (output_dir / "SHA256SUMS").write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in sha_inputs),
        encoding="utf-8",
    )


def _inventory(camp_head: str, dp_head: str) -> dict[str, Any]:
    matrix = PLAN_MODULE.NONFORMAL_MATRIX
    return {
        "camp_head": camp_head,
        "fixed_dp_head": dp_head,
        "routes": matrix["routes"],
        "npc_modes": matrix["npc_modes"],
        "traffic_light_modes": matrix["traffic_light_modes"],
        "scenario_buckets": PLAN_MODULE.SCENARIO_BUCKETS,
        "candidate_tensor_provenance": "fixed_dp_candidate_tensor_only",
        "camp_action": "rerank_or_select_only",
        "blocked_inputs": {
            "Full36": False,
            "formal_seeds_11_12_13": False,
            "closed_loop_outcomes_for_training_or_online_input": False,
        },
        "executions": {"training": False, "paired_evaluation": False},
        "mutations": {
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "trajectory_modified": False,
        },
    }


def _split_manifest() -> dict[str, Any]:
    matrix = PLAN_MODULE.NONFORMAL_MATRIX
    return {
        "train": {"seeds": matrix["train_seeds"]},
        "calibration": {"seeds": matrix["calibration_seeds"]},
        "holdout": {"seeds": matrix["holdout_seeds"]},
    }


def _zero_overlap_plan() -> dict[str, Any]:
    return {
        "zero_overlap_keys": (
            "route",
            "seed",
            "npc_mode",
            "traffic_light_mode",
            "candidate_tensor_sha256",
            "record_id",
        )
    }


def _scenario_bucket_manifest() -> dict[str, Any]:
    return {"scenario_buckets": PLAN_MODULE.SCENARIO_BUCKETS}


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    return "\n".join(
        [
            "# V15 Source Inventory",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "- Execution type: read-only source inventory materialization.",
            "",
        ]
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_sha256s(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(None, 1)
            entries[Path(name.strip()).name] = digest
    return entries


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
