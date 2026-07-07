#!/usr/bin/env python3
"""Static-review the v15 broader non-formal evidence expansion preflight."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_plan_module():
    plan_path = Path(__file__).resolve().with_name(
        "plan_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_preflight.py"
    )
    spec = importlib.util.spec_from_file_location("v15_broader_nonformal_preflight_plan", plan_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


PLAN_MODULE = _load_plan_module()

FIXED_DP_HEAD = PLAN_MODULE.FIXED_DP_HEAD
SCHEMA_VERSION = "dp_camp_v15_broader_nonformal_evidence_expansion_plan_preflight_static_review_v1"
AUTHORIZED_CURRENT_WORK = PLAN_MODULE.AUTHORIZED_NEXT_WORK
READY_STATUS = "v15_broader_nonformal_evidence_expansion_plan_preflight_static_review_passed"
REJECT_STATUS = "v15_broader_nonformal_evidence_expansion_plan_preflight_static_review_rejected"
AUTHORIZED_NEXT_WORK = "v15_broader_nonformal_evidence_expansion_source_inventory_preflight_only"
REVIEW_JSON_NAME = "v15_broader_nonformal_evidence_expansion_plan_preflight_static_review.json"
REVIEW_MD_NAME = "v15_broader_nonformal_evidence_expansion_plan_preflight_static_review.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_report_json", type=Path, required=True)
    parser.add_argument("--source_report_md", type=Path, required=True)
    parser.add_argument("--source_sha256s", type=Path, required=True)
    parser.add_argument("--v15_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v15_broader_nonformal_evidence_expansion_plan_preflight_static_review",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_artifact_dir=args.source_artifact_dir,
        source_report_json=args.source_report_json,
        source_report_md=args.source_report_md,
        source_sha256s=args.source_sha256s,
        v15_audit_md=args.v15_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v15_broader_nonformal_evidence_expansion_plan_preflight_static_review,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_artifact_dir: Path,
    source_report_json: Path,
    source_report_md: Path,
    source_sha256s: Path,
    v15_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact = source_artifact_dir.resolve()
    source_report = _read_json(source_report_json)
    timing = _read_json(artifact / "timing.json")
    root_sha256s = _read_sha256s(source_sha256s)
    heads = _parse_key_values((artifact / "HEADS").read_text(encoding="utf-8"))
    v15_text = v15_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")

    checks = [
        _expect("static_review_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("source_artifact_dir_exists", artifact.is_dir(), str(artifact), "directory"),
        _expect("source_json_path", source_report_json.resolve(), artifact / PLAN_MODULE.REPORT_JSON_NAME),
        _expect("source_md_path", source_report_md.resolve(), artifact / PLAN_MODULE.REPORT_MD_NAME),
        _expect("source_sha256s_path", source_sha256s.resolve(), artifact / "SHA256SUMS"),
        _expect("source_schema", source_report.get("schema_version"), PLAN_MODULE.SCHEMA_VERSION),
        _expect("source_passed", source_report["final_decision"].get("passed"), True),
        _expect("source_authorized_static_review", source_report["final_decision"].get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_training_not_executed", source_report["final_decision"].get("training_executed"), False),
        _expect("source_paired_eval_not_executed", source_report["final_decision"].get("paired_evaluation_executed"), False),
        _expect("source_full36_not_used", source_report["final_decision"].get("full36_used"), False),
        _expect("source_formal_seeds_not_used", source_report["final_decision"].get("formal_seed_11_12_13_used"), False),
        _expect("source_dp_not_modified", source_report["final_decision"].get("dp_modified"), False),
        _expect("source_candidate_tensor_not_modified", source_report["final_decision"].get("candidate_tensor_modified"), False),
        _expect("source_trajectory_not_modified", source_report["final_decision"].get("trajectory_modified"), False),
        _expect("heads_camp_head", heads.get("CAMP_HEAD"), source_report["heads"]["camp_head"]),
        _expect("heads_origin_main", heads.get("CAMP_ORIGIN_MAIN"), source_report["heads"]["camp_origin_main"]),
        _expect("heads_dp_head", heads.get("DP_HEAD"), FIXED_DP_HEAD),
        _expect("timing_training_not_executed", timing.get("training_executed"), False),
        _expect("timing_online_selector_not_executed", timing.get("online_selector_evaluation_executed"), False),
        _expect("timing_instrumentation_no_behavior_change", timing.get("timing_instrumentation_changes_selector_behavior"), False),
        _contains("audit_authorizes_static_review", v15_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
        _contains("status_authorizes_static_review", status_text, f"next_work_target={AUTHORIZED_CURRENT_WORK}"),
    ]
    for name in PLAN_MODULE.ARTIFACT_LAYOUT:
        checks.append(_check(f"artifact_has_{name}", (artifact / name).is_file(), str(artifact / name), "file"))
        if (artifact / name).is_file() and name in root_sha256s:
            checks.append(_expect(f"artifact_sha_{name}", _sha256(artifact / name), root_sha256s[name]))

    failed = [check["name"] for check in checks if not check["passed"]]
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": READY_STATUS if not failed else REJECT_STATUS,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "source_artifact": str(artifact),
        "source_report_json_sha256": _sha256(source_report_json),
        "source_report_md_sha256": _sha256(source_report_md),
        "source_sha256s_sha256": _sha256(source_sha256s),
        "source_timing_json_sha256": _sha256(artifact / "timing.json"),
        "source_timing_md_sha256": _sha256(artifact / "timing.md"),
        "checks": checks,
        "final_decision": {
            "passed": not failed,
            "status": READY_STATUS if not failed else REJECT_STATUS,
            "failed_checks": failed,
            "check_count": len(checks),
            "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "full36_used": False,
            "formal_seed_11_12_13_used": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "trajectory_modified": False,
        },
    }
    return _stable(report)


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
            "# V15 Preflight Static Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Source artifact: `{report['source_artifact']}`",
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


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


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
