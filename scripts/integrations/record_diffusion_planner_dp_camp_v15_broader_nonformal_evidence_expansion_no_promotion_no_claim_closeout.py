#!/usr/bin/env python3
"""Record the v15 no-promotion/no-claim closeout."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_result_review_module():
    path = Path(__file__).resolve().with_name(
        "review_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_paired_evaluation_execution_result.py"
    )
    spec = importlib.util.spec_from_file_location("v15_paired_evaluation_execution_result_review", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


RESULT_REVIEW_MODULE = _load_result_review_module()

FIXED_DP_HEAD = RESULT_REVIEW_MODULE.FIXED_DP_HEAD
SOURCE_REVIEW_SCHEMA = RESULT_REVIEW_MODULE.SCHEMA_VERSION
SOURCE_REVIEW_STATUS = RESULT_REVIEW_MODULE.READY_STATUS
SOURCE_REVIEW_JSON_NAME = RESULT_REVIEW_MODULE.REVIEW_JSON_NAME
SOURCE_REVIEW_MD_NAME = RESULT_REVIEW_MODULE.REVIEW_MD_NAME
AUTHORIZED_CURRENT_WORK = RESULT_REVIEW_MODULE.AUTHORIZED_NEXT_WORK

SCHEMA_VERSION = "dp_camp_v15_broader_nonformal_evidence_expansion_no_promotion_no_claim_closeout_record_v1"
READY_STATUS = "v15_broader_nonformal_evidence_expansion_no_promotion_no_claim_closeout_recorded"
REJECT_STATUS = "v15_broader_nonformal_evidence_expansion_no_promotion_no_claim_closeout_rejected"
AUTHORIZED_NEXT_WORK = "no_further_action_v15_broader_nonformal_evidence_expansion_no_promotion_no_claim_closeout_complete"
RECORD_JSON_NAME = "v15_broader_nonformal_evidence_expansion_no_promotion_no_claim_closeout_record.json"
RECORD_MD_NAME = "v15_broader_nonformal_evidence_expansion_no_promotion_no_claim_closeout_record.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_result_review_artifact_dir", type=Path, required=True)
    parser.add_argument("--source_result_review_json", type=Path, required=True)
    parser.add_argument("--source_result_review_md", type=Path, required=True)
    parser.add_argument("--source_result_review_sha256s", type=Path, required=True)
    parser.add_argument("--v15_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v15_broader_nonformal_evidence_expansion_no_promotion_no_claim_closeout_record",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_result_review_artifact_dir=args.source_result_review_artifact_dir,
        source_result_review_json=args.source_result_review_json,
        source_result_review_md=args.source_result_review_md,
        source_result_review_sha256s=args.source_result_review_sha256s,
        v15_audit_md=args.v15_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v15_broader_nonformal_evidence_expansion_no_promotion_no_claim_closeout_record,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_result_review_artifact_dir: Path,
    source_result_review_json: Path,
    source_result_review_md: Path,
    source_result_review_sha256s: Path,
    v15_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    artifact = source_result_review_artifact_dir.resolve()
    source_json = source_result_review_json.resolve()
    source_md = source_result_review_md.resolve()
    source_sha256s = source_result_review_sha256s.resolve()
    source_review = _read_json(source_json)
    v15_text = v15_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")
    heads = _read_key_values(artifact / "HEADS")
    sha256s = _read_sha256s(source_sha256s)
    run_exit = _read_text_if_file(artifact / "run.exit").strip()
    checks = _checks(
        enabled=enabled,
        artifact=artifact,
        source_json=source_json,
        source_md=source_md,
        source_sha256s=source_sha256s,
        source_review=source_review,
        v15_text=v15_text,
        status_text=status_text,
        heads=heads,
        sha256s=sha256s,
        run_exit=run_exit,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    return _stable(
        {
            "schema_version": SCHEMA_VERSION,
            "inputs": {
                "source_result_review_artifact_dir": str(artifact),
                "source_result_review_json": str(source_json),
                "source_result_review_md": str(source_md),
                "source_result_review_sha256s": str(source_sha256s),
                "v15_audit_md": str(v15_audit_md.resolve()),
                "current_status_md": str(current_status_md.resolve()),
                "output_dir": str(output_dir.resolve()),
            },
            "heads": {
                "current_camp_head": current_camp_head,
                "current_camp_origin_main": current_camp_origin_main,
                "current_dp_head": current_dp_head,
                "required_dp_head": required_dp_head,
                "source_artifact_camp_head": _kv(heads, "CAMP_HEAD", "camp_head"),
                "source_artifact_camp_origin_main": _kv(heads, "CAMP_ORIGIN_MAIN", "camp_origin_main"),
                "source_artifact_dp_head": _kv(heads, "DP_HEAD", "dp_head"),
            },
            "source_artifact_hashes": _source_hashes(
                artifact=artifact,
                source_json=source_json,
                source_md=source_md,
                source_sha256s=source_sha256s,
            ),
            "source_result_review_summary": _source_result_review_summary(source_review),
            "closeout_summary": _closeout_summary(source_review),
            "closeout_checks": checks,
            "final_decision": _decision(failed=failed, source_review=source_review),
        }
    )


def _checks(
    *,
    enabled: bool,
    artifact: Path,
    source_json: Path,
    source_md: Path,
    source_sha256s: Path,
    source_review: dict[str, Any],
    v15_text: str,
    status_text: str,
    heads: dict[str, str],
    sha256s: dict[str, str],
    run_exit: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
) -> list[dict[str, Any]]:
    decision = _dict(source_review.get("final_decision"))
    checks = [
        _expect("closeout_record_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("source_result_review_artifact_exists", artifact.is_dir(), str(artifact), "directory"),
        _check("source_result_review_json_exists", source_json.is_file(), str(source_json), "file"),
        _check("source_result_review_md_exists", source_md.is_file(), str(source_md), "file"),
        _check("source_result_review_sha256s_exists", source_sha256s.is_file(), str(source_sha256s), "file"),
        _check("source_result_review_heads_exists", (artifact / "HEADS").is_file(), str(artifact / "HEADS"), "file"),
        _check("source_result_review_command_exists", (artifact / "COMMAND").is_file(), str(artifact / "COMMAND"), "file"),
        _check("source_result_review_stdout_exists", _has_any(artifact, ("stdout.txt", "stdout")), "stdout", "file"),
        _check("source_result_review_stderr_exists", _has_any(artifact, ("stderr.txt", "stderr")), "stderr", "file"),
        _check("source_result_review_run_exit_exists", (artifact / "run.exit").is_file(), str(artifact / "run.exit"), "file"),
        _expect("source_result_review_run_exit", run_exit, "0"),
        _expect("source_artifact_dp_head_fixed", _kv(heads, "DP_HEAD", "dp_head"), required_dp_head),
        _expect("audit_latest_status", _latest_value(v15_text, "current_v15_status"), SOURCE_REVIEW_STATUS),
        _expect("audit_latest_next_work", _latest_value(v15_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("status_doc_latest_status", _latest_value(status_text, "current_v15_status"), SOURCE_REVIEW_STATUS),
        _expect("status_doc_latest_next_work", _latest_value(status_text, "next_work_target"), AUTHORIZED_CURRENT_WORK),
        _expect("source_result_review_schema", source_review.get("schema_version"), SOURCE_REVIEW_SCHEMA),
        _expect("source_result_review_passed", decision.get("passed"), True),
        _expect("source_result_review_status", decision.get("status"), SOURCE_REVIEW_STATUS),
        _expect("source_result_review_failed_checks", decision.get("failed_checks"), []),
        _expect("source_result_review_authorized_current_work", decision.get("authorized_next_work"), AUTHORIZED_CURRENT_WORK),
        _expect("source_result_review_reviewed_execution", decision.get("reviewed_paired_evaluation_execution"), True),
        _expect("source_result_review_source_execution_executed", decision.get("source_paired_evaluation_executed"), True),
        _expect("source_result_review_training_not_executed", decision.get("training_executed"), False),
        _expect("source_result_review_paired_eval_not_executed", decision.get("paired_evaluation_executed"), False),
        _expect("source_result_review_online_latency_not_executed", decision.get("online_selector_latency_executed"), False),
        _expect("source_result_review_fallback_latency_not_executed", decision.get("fallback_latency_executed"), False),
        _expect("source_result_review_performance_not_claimed", decision.get("performance_claimed"), False),
        _expect("source_result_review_promotion_not_supported", decision.get("promotion_supported"), False),
        _expect("source_result_review_closeout_record_authorized", decision.get("closeout_record_authorized"), True),
        _expect("source_result_review_full36_not_used", decision.get("full36_used"), False),
        _expect("source_result_review_formal_seed_not_used", decision.get("formal_seed_11_12_13_used"), False),
        _expect("source_result_review_dp_not_modified", decision.get("dp_modified"), False),
        _expect("source_result_review_candidate_tensor_not_modified", decision.get("candidate_tensor_modified"), False),
        _expect("source_result_review_trajectory_not_modified", decision.get("trajectory_modified"), False),
        _expect("source_result_review_json_sha", _sha256(source_json), sha256s.get(source_json.name)),
        _expect("source_result_review_md_sha", _sha256(source_md), sha256s.get(source_md.name)),
    ]
    return checks


def _decision(*, failed: list[str], source_review: dict[str, Any]) -> dict[str, Any]:
    source_decision = _dict(source_review.get("final_decision"))
    passed = not failed
    if passed:
        failure_class = None
    elif "closeout_record_enabled" in failed:
        failure_class = "explicit_closeout_record_authorization_missing"
    elif any(name.startswith(("audit_", "status_doc_")) for name in failed):
        failure_class = "v15_eof_contract_mismatch"
    elif any("dp_head" in name for name in failed):
        failure_class = "fixed_dp_head_mismatch"
    elif any(name.startswith("source_result_review_") for name in failed):
        failure_class = "source_result_review_contract_failure"
    else:
        failure_class = "artifact_hash_or_closeout_contract_failure"
    return {
        "passed": passed,
        "status": READY_STATUS if passed else REJECT_STATUS,
        "failure_class": failure_class,
        "failed_checks": failed,
        "check_count": len(failed) if failed else 0,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "closeout_recorded": passed,
        "no_further_action_recommended": passed,
        "reviewed_paired_evaluation_execution": bool(source_decision.get("reviewed_paired_evaluation_execution")),
        "source_paired_evaluation_executed": bool(source_decision.get("source_paired_evaluation_executed")),
        "training_executed": False,
        "paired_evaluation_executed": False,
        "online_selector_latency_executed": False,
        "fallback_latency_executed": False,
        "performance_claimed": False,
        "promotion_supported": False,
        "full36_used": False,
        "formal_seed_11_12_13_used": False,
        "dp_modified": False,
        "candidate_tensor_modified": False,
        "trajectory_modified": False,
        "recommendation": "stop_no_promotion_no_claim_closeout_complete" if passed else "repair_or_rerun_same_closeout_gate",
    }


def _source_result_review_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_review.get("final_decision"))
    review = _dict(source_review.get("result_review"))
    return {
        "passed": decision.get("passed"),
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "reviewed_paired_evaluation_execution": decision.get("reviewed_paired_evaluation_execution"),
        "source_paired_evaluation_executed": decision.get("source_paired_evaluation_executed"),
        "paired_rows": review.get("paired_rows"),
        "calibration_rows": review.get("calibration_rows"),
        "holdout_rows": review.get("holdout_rows"),
        "train_rows": review.get("train_rows"),
        "performance_claimed": decision.get("performance_claimed"),
        "promotion_supported": decision.get("promotion_supported"),
        "closeout_record_authorized": decision.get("closeout_record_authorized"),
    }


def _closeout_summary(source_review: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(source_review.get("final_decision"))
    review = _dict(source_review.get("result_review"))
    return {
        "closeout_classification": "no_promotion_no_claim",
        "closeout_reason": "paired_evaluation_did_not_support_performance_claim_or_promotion",
        "source_closeout_classification": review.get("closeout_classification"),
        "performance_claimed": False,
        "promotion_supported": False,
        "source_performance_claimed": decision.get("performance_claimed"),
        "source_promotion_supported": decision.get("promotion_supported"),
        "no_promotion_no_claim": True,
    }


def _source_hashes(*, artifact: Path, source_json: Path, source_md: Path, source_sha256s: Path) -> dict[str, Any]:
    return {
        "source_result_review_json_sha256": _sha256_if_file(source_json),
        "source_result_review_md_sha256": _sha256_if_file(source_md),
        "source_result_review_sha256s_sha256": _sha256_if_file(source_sha256s),
        "heads_sha256": _sha256_if_file(artifact / "HEADS"),
        "command_sha256": _sha256_if_file(artifact / "COMMAND"),
        "stdout_sha256": _sha256_if_file(_first_existing(artifact, ("stdout.txt", "stdout"))),
        "stderr_sha256": _sha256_if_file(_first_existing(artifact, ("stderr.txt", "stderr"))),
        "run_exit_sha256": _sha256_if_file(artifact / "run.exit"),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / RECORD_JSON_NAME
    md_path = output_dir / RECORD_MD_NAME
    json_path.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        f"{_sha256(json_path)}  {json_path.name}\n{_sha256(md_path)}  {md_path.name}\n",
        encoding="utf-8",
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    closeout = report["closeout_summary"]
    return "\n".join(
        [
            "# V15 No-Promotion/No-Claim Closeout",
            "",
            f"- Passed: `{decision['passed']}`",
            f"- Status: `{decision['status']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            "",
            "## Closeout",
            "",
            f"- Classification: `{closeout['closeout_classification']}`",
            f"- Reason: `{closeout['closeout_reason']}`",
            f"- Performance claimed: `{decision['performance_claimed']}`",
            f"- Promotion supported: `{decision['promotion_supported']}`",
            f"- No further action recommended: `{decision['no_further_action_recommended']}`",
            "",
            "## Boundary",
            "",
            "- Record only: no training, paired evaluation, online selector latency run, fallback latency run, DP modification, candidate tensor mutation, trajectory mutation, promotion, or claim.",
            "- Full36 and formal seeds 11/12/13 remain unused.",
            "",
        ]
    )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _read_key_values(path: Path) -> dict[str, str]:
    return _parse_key_values(_read_text_if_file(path))


def _parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            values[key.strip()] = value.strip()
    return values


def _read_sha256s(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(None, 1)
            entries[Path(name.strip()).name] = digest
    return entries


def _latest_value(text: str, key: str) -> str | None:
    token = f"{key}="
    if token not in text:
        return None
    return text.rsplit(token, maxsplit=1)[1].splitlines()[0]


def _kv(values: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        if key in values:
            return values[key]
    return None


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _has_any(root: Path, names: tuple[str, ...]) -> bool:
    return any((root / name).is_file() for name in names)


def _first_existing(root: Path, names: tuple[str, ...]) -> Path:
    for name in names:
        path = root / name
        if path.is_file():
            return path
    return root / names[0]


def _read_text_if_file(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_if_file(path: Path) -> str | None:
    return _sha256(path) if path.is_file() else None


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
