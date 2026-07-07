#!/usr/bin/env python3
"""Plan the v16 100-1000 nuScenes fixed-DP candidate tensor smoke."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_source_review_module():
    path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_adapter_plan_static_contract.py"
    )
    spec = importlib.util.spec_from_file_location("v16_nuscenes_adapter_plan_static_review", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


SOURCE_REVIEW_MODULE = _load_source_review_module()
FIXED_DP_HEAD = SOURCE_REVIEW_MODULE.FIXED_DP_HEAD
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke_preflight_plan_v1"
AUTHORIZED_CURRENT_WORK = SOURCE_REVIEW_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_preflight_plan_ready"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_preflight_plan_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_preflight_plan_static_review_only"
PLAN_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_preflight_plan.json"
PLAN_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_preflight_plan.md"
MUST_RECORD = (
    "adapter_input_shape",
    "candidate_tensor_shape",
    "candidate_tensor_sha256",
    "dp_top1_index",
    "camp_atom_table_sha256",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_static_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_static_review_json", type=Path, required=True)
    parser.add_argument("--source_static_review_md", type=Path, required=True)
    parser.add_argument("--source_static_review_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--enable_v16_nuscenes_fixed_dp_candidate_tensor_smoke_preflight_plan", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_static_review_artifact_dir=args.source_static_review_artifact_dir,
        source_static_review_json=args.source_static_review_json,
        source_static_review_md=args.source_static_review_md,
        source_static_review_sha256s=args.source_static_review_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_smoke_preflight_plan,
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
    v16_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    del output_dir
    artifact = source_static_review_artifact_dir.resolve()
    source = _read_json(source_static_review_json)
    source_sha256s = _read_sha256s(source_static_review_sha256s)
    v16_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    plan = _smoke_preflight_plan()
    source_records = _source_smoke_records(source.get("smoke_contract", {}))
    checks = [
        _expect("smoke_preflight_plan_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("source_static_review_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_static_review_json_path", source_static_review_json.resolve(), artifact / SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME),
        _expect("source_static_review_md_path", source_static_review_md.resolve(), artifact / SOURCE_REVIEW_MODULE.REVIEW_MD_NAME),
        _expect("source_static_review_sha256s_path", source_static_review_sha256s.resolve(), artifact / "SHA256SUMS"),
        _expect("source_static_review_schema", source.get("schema_version"), SOURCE_REVIEW_MODULE.SCHEMA_VERSION),
        _expect("source_static_review_passed", source["final_decision"].get("passed"), True),
        _expect("source_authorizes_smoke_preflight_plan", source["final_decision"].get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_static_review_only", source["final_decision"].get("static_review_only"), True),
        _expect("source_adapter_not_executed", source["final_decision"].get("adapter_execution_executed"), False),
        _expect("source_candidate_generation_not_executed", source["final_decision"].get("candidate_generation_executed"), False),
        _expect("source_training_not_executed", source["final_decision"].get("training_executed"), False),
        _expect("source_paired_eval_not_executed", source["final_decision"].get("paired_evaluation_executed"), False),
        _expect("source_dp_not_modified", source["final_decision"].get("dp_modified"), False),
        _expect("source_candidate_tensor_not_modified", source["final_decision"].get("candidate_tensor_modified"), False),
        _expect("source_trajectory_not_modified", source["final_decision"].get("trajectory_modified"), False),
        _contains("audit_authorizes_smoke_preflight_plan", v16_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _check(
            "status_authorizes_smoke_preflight_plan",
            _status_authorizes_this_or_same_gate_rerun(status_text),
            _latest_v16_status_block(status_text),
            f"next_work_target={AUTHORIZED_CURRENT_WORK} or same-gate rerun",
        ),
        _contains("audit_records_adapter_plan_static_review", v16_text, f"current_v16_status={SOURCE_REVIEW_MODULE.READY_STATUS}"),
        _check(
            "status_records_adapter_plan_static_review",
            _records_source_static_review(status_text),
            _latest_v16_status_block(status_text),
            "source static-review status or artifact reference",
        ),
        _expect("smoke_min_records", plan["records"]["min_records"], 100),
        _expect("smoke_max_records", plan["records"]["max_records"], 1000),
        _expect("smoke_k", plan["candidate_generation"]["k"], 8),
        _expect("smoke_candidate_count", plan["candidate_generation"]["candidate_count"], 8),
        _expect("smoke_blocks_training", plan["blocked_until_smoke_passes"]["train_camp"], True),
    ]
    for name in (
        "HEADS",
        "COMMAND",
        "stdout.txt",
        "stderr.txt",
        "run.exit",
        SOURCE_REVIEW_MODULE.REVIEW_JSON_NAME,
        SOURCE_REVIEW_MODULE.REVIEW_MD_NAME,
    ):
        path = artifact / name
        checks.append(_check(f"source_artifact_has_{name}", path.is_file(), str(path), "file"))
        if path.is_file() and name in source_sha256s:
            checks.append(_expect(f"source_artifact_sha_{name}", _sha256(path), source_sha256s[name]))
    for record in MUST_RECORD:
        checks.append(_check(f"source_records_{record}", record in source_records, record, "present"))
        checks.append(_check(f"smoke_plan_records_{record}", record in plan["must_record"], record, "present"))

    failed = [check["name"] for check in checks if not check["passed"]]
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if not failed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK,
            "source_static_review_artifact": str(artifact),
            "smoke_preflight_plan": plan,
            "artifact_layout": (
                "HEADS",
                "COMMAND",
                "stdout.txt",
                "stderr.txt",
                "run.exit",
                PLAN_JSON_NAME,
                PLAN_MD_NAME,
                "SHA256SUMS",
            ),
            "checks": checks,
            "final_decision": {
                "passed": not failed,
                "status": READY_STATUS if not failed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
                "candidate_generation_executed": False,
                "training_executed": False,
                "paired_evaluation_executed": False,
                "performance_claimed": False,
                "full36_used": False,
                "formal_seed_11_12_13_used": False,
                "dp_modified": False,
                "candidate_tensor_modified": False,
                "trajectory_modified": False,
            },
        }
    )


def _smoke_preflight_plan() -> dict[str, Any]:
    return {
        "records": {"min_records": 100, "max_records": 1000},
        "candidate_generation": {
            "k": 8,
            "candidate_count": 8,
            "k16_ablation_only_after_k8_passes": True,
        },
        "must_record": MUST_RECORD,
        "must_verify": (
            "fixed_dp_head",
            "adapter_input_shape",
            "candidate_tensor_shape",
            "candidate_tensor_sha256",
            "dp_top1_index",
            "camp_atom_table_sha256",
            "no_training",
            "no_candidate_mutation",
        ),
        "blocked_until_smoke_passes": {
            "expand_to_10k": True,
            "train_camp": True,
            "paired_holdout_eval": True,
            "performance_claim": True,
        },
        "latency_fields": ("adapter_conversion_ms", "dp_candidate_generation_ms", "camp_atom_extraction_ms"),
        "split": "smoke_only_not_train_not_holdout_claim",
    }


def _source_smoke_records(smoke_contract: dict[str, Any]) -> tuple[str, ...]:
    explicit = smoke_contract.get("must_record")
    if explicit is not None:
        return tuple(explicit)
    if smoke_contract.get("must_record_candidate_tensor_shape_hash") is True:
        return MUST_RECORD
    return ()


def _status_authorizes_this_or_same_gate_rerun(text: str) -> bool:
    return f"next_work_target={AUTHORIZED_CURRENT_WORK}" in text or (
        f"current_v16_status={READY_STATUS}" in text
        and f"next_work_target={AUTHORIZED_NEXT_WORK}" in text
    )


def _records_source_static_review(text: str) -> bool:
    return (
        f"current_v16_status={SOURCE_REVIEW_MODULE.READY_STATUS}" in text
        or "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_adapter_plan_static_review" in text
    )


def _latest_v16_status_block(text: str) -> str:
    lines = [
        line
        for line in text.splitlines()
        if line.startswith(("current_v16_status=", "next_work_target="))
    ]
    return ";".join(lines[-2:])


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / PLAN_JSON_NAME
    md_path = output_dir / PLAN_MD_NAME
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        f"{_sha256(json_path)}  {json_path.name}\n{_sha256(md_path)}  {md_path.name}\n",
        encoding="utf-8",
    )


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    plan = report["smoke_preflight_plan"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Smoke Preflight Plan",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Records: `{plan['records']['min_records']}-{plan['records']['max_records']}`",
            "- Training: `False`",
            "- Candidate mutation: `False`",
            "",
        ]
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_sha256s(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
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
        return {str(key): _stable(value[key]) for key in sorted(value)}
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
