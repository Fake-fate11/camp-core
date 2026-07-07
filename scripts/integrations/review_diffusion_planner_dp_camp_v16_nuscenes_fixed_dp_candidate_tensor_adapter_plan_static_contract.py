#!/usr/bin/env python3
"""Static-review the v16 nuScenes fixed-DP candidate tensor adapter plan."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_plan_module():
    path = Path(__file__).resolve().with_name(
        "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_adapter.py"
    )
    spec = importlib.util.spec_from_file_location("v16_nuscenes_adapter_plan", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PLAN_MODULE = _load_plan_module()
FIXED_DP_HEAD = PLAN_MODULE.FIXED_DP_HEAD
SCHEMA_VERSION = "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_adapter_plan_static_review_v1"
AUTHORIZED_CURRENT_WORK = PLAN_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_adapter_plan_static_review_passed"
REJECT_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_adapter_plan_static_review_rejected"
AUTHORIZED_NEXT_WORK = "v16_nuscenes_fixed_dp_candidate_tensor_smoke_preflight_plan_only"
REVIEW_JSON_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_adapter_plan_static_review.json"
REVIEW_MD_NAME = "v16_nuscenes_fixed_dp_candidate_tensor_adapter_plan_static_review.md"
SMOKE_RECORDS = (
    "adapter_input_shape",
    "candidate_tensor_shape",
    "candidate_tensor_sha256",
    "dp_top1_index",
    "camp_atom_table_sha256",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter_plan_artifact_dir", type=Path, required=True)
    parser.add_argument("--adapter_plan_json", type=Path, required=True)
    parser.add_argument("--adapter_plan_md", type=Path, required=True)
    parser.add_argument("--adapter_plan_sha256s", type=Path, required=True)
    parser.add_argument("--v16_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--enable_v16_nuscenes_fixed_dp_candidate_tensor_adapter_plan_static_review", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        adapter_plan_artifact_dir=args.adapter_plan_artifact_dir,
        adapter_plan_json=args.adapter_plan_json,
        adapter_plan_md=args.adapter_plan_md,
        adapter_plan_sha256s=args.adapter_plan_sha256s,
        v16_audit_md=args.v16_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v16_nuscenes_fixed_dp_candidate_tensor_adapter_plan_static_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    adapter_plan_artifact_dir: Path,
    adapter_plan_json: Path,
    adapter_plan_md: Path,
    adapter_plan_sha256s: Path,
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
    artifact = adapter_plan_artifact_dir.resolve()
    source = _read_json(adapter_plan_json)
    source_sha256s = _read_sha256s(adapter_plan_sha256s)
    v16_text = v16_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    plan = source.get("adapter_plan", {})
    smoke = plan.get("smoke", {})
    tensor_contract = plan.get("candidate_tensor_contract", {})
    atom_contract = plan.get("camp_atom_contract", {})
    checks = [
        _expect("static_review_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("adapter_plan_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("adapter_plan_json_path", adapter_plan_json.resolve(), artifact / PLAN_MODULE.PLAN_JSON_NAME),
        _expect("adapter_plan_md_path", adapter_plan_md.resolve(), artifact / PLAN_MODULE.PLAN_MD_NAME),
        _expect("adapter_plan_sha256s_path", adapter_plan_sha256s.resolve(), artifact / "SHA256SUMS"),
        _expect("adapter_plan_schema", source.get("schema_version"), PLAN_MODULE.SCHEMA_VERSION),
        _expect("adapter_plan_passed", source["final_decision"].get("passed"), True),
        _expect("adapter_plan_authorizes_static_review", source["final_decision"].get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_adapter_not_executed", source["final_decision"].get("adapter_execution_executed"), False),
        _expect("source_candidate_generation_not_executed", source["final_decision"].get("candidate_generation_executed"), False),
        _expect("source_training_not_executed", source["final_decision"].get("training_executed"), False),
        _expect("source_paired_eval_not_executed", source["final_decision"].get("paired_evaluation_executed"), False),
        _expect("source_dp_not_modified", source["final_decision"].get("dp_modified"), False),
        _expect("source_candidate_tensor_not_modified", source["final_decision"].get("candidate_tensor_modified"), False),
        _expect("source_trajectory_not_modified", source["final_decision"].get("trajectory_modified"), False),
        _contains("audit_authorizes_static_review", v16_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_static_review", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("audit_records_adapter_plan", v16_text, f"current_v16_status={PLAN_MODULE.READY_STATUS}"),
        _contains("status_records_adapter_plan", status_text, f"current_v16_status={PLAN_MODULE.READY_STATUS}"),
        _expect("adapter_dp_commit_fixed", tensor_contract.get("dp_commit"), FIXED_DP_HEAD),
        _expect("adapter_candidate_tensor_immutable", tensor_contract.get("immutable_after_dp"), True),
        _expect("camp_score_affine", atom_contract.get("score"), "score_k(w)=a_k^T w"),
        _expect("camp_weights_simplex", atom_contract.get("weights"), "nonnegative_simplex"),
        _expect("camp_no_trajectory_mutation", atom_contract.get("trajectory_generation_repair_rewrite_blend"), False),
        _expect("smoke_min_records", smoke.get("min_records"), 100),
        _expect("smoke_max_records", smoke.get("max_records"), 1000),
        _expect("smoke_training_not_executed", smoke.get("training_executed"), False),
    ]
    for name in (
        "HEADS",
        "COMMAND",
        "stdout.txt",
        "stderr.txt",
        "run.exit",
        PLAN_MODULE.PLAN_JSON_NAME,
        PLAN_MODULE.PLAN_MD_NAME,
    ):
        path = artifact / name
        checks.append(_check(f"source_artifact_has_{name}", path.is_file(), str(path), "file"))
        if path.is_file() and name in source_sha256s:
            checks.append(_expect(f"source_artifact_sha_{name}", _sha256(path), source_sha256s[name]))
    input_mapping = plan.get("input_mapping", {})
    for requirement in PLAN_MODULE.SOURCE_REVIEW_MODULE.PREFLIGHT_MODULE.DP_INPUT_REQUIREMENTS:
        checks.append(_check(f"adapter_plan_maps_{requirement}", requirement in input_mapping, requirement, "mapped"))
    must_record = smoke.get("must_record", [])
    for record in SMOKE_RECORDS:
        checks.append(
            _check(
                f"adapter_plan_records_{record}",
                record in must_record,
                record,
                "present",
            )
        )

    failed = [check["name"] for check in checks if not check["passed"]]
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "status": READY_STATUS if not failed else REJECT_STATUS,
            "authorized_current_work": AUTHORIZED_CURRENT_WORK,
            "authorized_next_work": AUTHORIZED_NEXT_WORK,
            "adapter_plan_artifact": str(artifact),
            "adapter_contract": {"candidate_tensor_immutable_after_dp": tensor_contract.get("immutable_after_dp")},
            "smoke_contract": {"must_record_candidate_tensor_shape_hash": all(x in must_record for x in ("candidate_tensor_shape", "candidate_tensor_sha256"))},
            "checks": checks,
            "final_decision": {
                "passed": not failed,
                "status": READY_STATUS if not failed else REJECT_STATUS,
                "failed_checks": failed,
                "check_count": len(checks),
                "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
                "static_review_only": True,
                "adapter_execution_executed": False,
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


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REVIEW_JSON_NAME
    md_path = output_dir / REVIEW_MD_NAME
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        f"{_sha256(json_path)}  {json_path.name}\n{_sha256(md_path)}  {md_path.name}\n",
        encoding="utf-8",
    )


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Candidate Tensor Adapter Plan Static Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
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
