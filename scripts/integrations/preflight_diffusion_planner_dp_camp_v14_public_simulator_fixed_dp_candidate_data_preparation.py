#!/usr/bin/env python3
"""V14 public-simulator fixed-DP candidate data-preparation preflight.

This read-only gate validates that the zero-overlap fixed DP candidate replay
outputs are suitable as the next CAMP training-input source. It does not run
replay, generate candidates, prepare training arrays, train CAMP, modify DP,
promote, deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.validate_dp_native_training_data_contract import (  # noqa: E402
    validate_logs,
)


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_fixed_dp_candidate_data_preparation_preflight_v1"
)
TRAINING_INPUT_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_fixed_dp_candidate_training_input_manifest_v1"
)
EXPECTED_CURRENT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_data_preparation_preflight"
)
AUTHORIZED_NEXT_WORK = "public_simulator_fixed_dp_candidate_generation_training_preflight"
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_data_preparation_preflight_ready"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_data_preparation_preflight_rejected"
)
EXPECTED_LOG_COUNT = 32
EXPECTED_STEPS_PER_LOG = 100
EXPECTED_RECORDS = 3200
EXPECTED_NUM_CANDIDATES = 8
FORMAL_SEEDS = {11, 12, 13}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution_output_root", type=Path, required=True)
    parser.add_argument("--zero_overlap_artifact_dir", type=Path, required=True)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        execution_output_root=args.execution_output_root,
        zero_overlap_artifact_dir=args.zero_overlap_artifact_dir,
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    execution_output_root: Path,
    zero_overlap_artifact_dir: Path,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
) -> dict[str, Any]:
    execution_output_root = execution_output_root.resolve()
    zero_overlap_artifact_dir = zero_overlap_artifact_dir.resolve()
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    zero = _load_zero_overlap_artifact(zero_overlap_artifact_dir)
    selection_logs = _selection_logs_from_artifact(zero, execution_output_root)
    training_contract = validate_logs(selection_logs) if selection_logs else _empty_contract()
    checks = _checks(
        execution_output_root=execution_output_root,
        zero_overlap_artifact_dir=zero_overlap_artifact_dir,
        zero=zero,
        selection_logs=selection_logs,
        training_contract=training_contract,
        v14_audit_md=v14_audit_md,
        current_status_md=current_status_md,
        v14_text=v14_text,
        status_text=status_text,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    training_input_manifest = _training_input_manifest(
        execution_output_root=execution_output_root,
        zero_overlap_artifact_dir=zero_overlap_artifact_dir,
        output_dir=output_dir,
        selection_logs=selection_logs,
        zero=zero,
        training_contract=training_contract,
        current_camp_head=current_camp_head,
        current_dp_head=current_dp_head,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "data_preparation_preflight_only": True,
            "read_only": True,
            "data_preparation_executed": False,
            "fixed_dp_candidate_generation_executed_by_source": True,
            "zero_overlap_validation_executed_by_source": True,
            "training_execution": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "dp_modification": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "approved_atoms_nonnegative_simplex_only": True,
            "simplex_cvar_l2_master_convexity_preserved": True,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "inputs": {
            "execution_output_root": str(execution_output_root),
            "zero_overlap_artifact_dir": str(zero_overlap_artifact_dir),
            "v14_audit_md": str(v14_audit_md),
            "current_status_md": str(current_status_md),
            "output_dir": str(output_dir),
        },
        "zero_overlap_summary": zero["summary"],
        "zero_overlap_intersections": zero["intersections"],
        "training_data_contract": training_contract,
        "selection_log_count": len(selection_logs),
        "selection_logs": [str(path) for path in selection_logs],
        "planned_outputs": {
            "training_input_manifest_json": str(output_dir / "training_input_manifest.json"),
            "preflight_report_json": str(output_dir / "data_preparation_preflight_report.json"),
            "preflight_report_md": str(output_dir / "data_preparation_preflight_report.md"),
            "runbook": str(output_dir / "run_data_preparation_preflight.sh"),
            "sha256sums": str(output_dir / "SHA256SUMS"),
        },
        "training_input_manifest": training_input_manifest,
        "checks": checks,
        "final_decision": _decision(
            passed=passed,
            failed=failed,
            authorized_current_work=authorized_current_work,
            authorized_next_work=authorized_next_work,
        ),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "training_input_manifest.json", report["training_input_manifest"])
    slim = dict(report)
    slim.pop("training_input_manifest", None)
    slim.pop("selection_logs", None)
    _write_json(output_dir / "data_preparation_preflight_report.json", slim)
    (output_dir / "data_preparation_preflight_report.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    (output_dir / "run_data_preparation_preflight.sh").write_text(
        render_runbook(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def _load_zero_overlap_artifact(path: Path) -> dict[str, Any]:
    report = _read_json(path / "zero_overlap_validation_report.json")
    selection_logs = _read_json(path / "selection_logs.json")
    if not isinstance(selection_logs, list):
        selection_logs = []
    registries = {
        name: _read_json(path / f"{name}.json")
        for name in (
            "candidate_tensor_hash_registry",
            "path_signature_registry",
            "record_identity_hash_registry",
            "split_manifest_root_registry",
        )
    }
    return {
        "report": report if isinstance(report, dict) else {},
        "selection_logs": [str(item) for item in selection_logs],
        "registries": registries,
        "summary": _dict(report.get("registry_summary") if isinstance(report, dict) else {}),
        "intersections": _dict(
            report.get("zero_intersection_counts") if isinstance(report, dict) else {}
        ),
        "decision": _dict(report.get("final_decision") if isinstance(report, dict) else {}),
    }


def _selection_logs_from_artifact(
    zero: dict[str, Any],
    execution_output_root: Path,
) -> list[Path]:
    paths = [Path(path) for path in zero["selection_logs"]]
    if not paths:
        paths = sorted(execution_output_root.rglob("camp_selection_log.json"))
    return sorted(paths)


def _checks(
    *,
    execution_output_root: Path,
    zero_overlap_artifact_dir: Path,
    zero: dict[str, Any],
    selection_logs: list[Path],
    training_contract: dict[str, Any],
    v14_audit_md: Path,
    current_status_md: Path,
    v14_text: str,
    status_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    add = checks.append
    decision = zero["decision"]
    summary = zero["summary"]
    intersections = zero["intersections"]

    add(_expect("execution_output_root_exists", execution_output_root.is_dir(), True))
    add(_expect("zero_overlap_artifact_dir_exists", zero_overlap_artifact_dir.is_dir(), True))
    add(_expect("zero_overlap_report_exists", (zero_overlap_artifact_dir / "zero_overlap_validation_report.json").is_file(), True))
    add(_expect("zero_overlap_selection_logs_exists", (zero_overlap_artifact_dir / "selection_logs.json").is_file(), True))
    for name in (
        "candidate_tensor_hash_registry",
        "path_signature_registry",
        "record_identity_hash_registry",
        "split_manifest_root_registry",
    ):
        add(_expect(f"{name}_exists", (zero_overlap_artifact_dir / f"{name}.json").is_file(), True))
    add(_expect("v14_audit_exists", v14_audit_md.is_file(), True))
    add(_expect("current_status_exists", current_status_md.is_file(), True))
    add(_expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), EXPECTED_CURRENT_STATUS))
    add(_expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), authorized_current_work))
    add(_expect("status_doc_current_status", EXPECTED_CURRENT_STATUS in status_text, True))
    add(_expect("status_doc_next_work", authorized_current_work in status_text, True))
    add(_expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main))
    add(_expect("current_dp_head_fixed", current_dp_head, required_dp_head))
    add(_expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD))
    add(_expect("zero_overlap_passed", decision.get("passed"), True))
    add(
        _expect(
            "zero_overlap_status",
            decision.get("status"),
            "public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_passed",
        )
    )
    add(_expect("zero_overlap_authorizes_current_work", decision.get("authorized_next_work"), authorized_current_work))
    add(_expect("zero_overlap_failed_checks_empty", decision.get("failed_checks"), []))
    add(_expect("selection_log_count", len(selection_logs), EXPECTED_LOG_COUNT))
    add(_expect("zero_summary_selection_log_count", summary.get("selection_log_count"), EXPECTED_LOG_COUNT))
    add(_expect("zero_summary_record_count", summary.get("record_count"), EXPECTED_RECORDS))
    add(_expect("zero_summary_wrong_step_logs_empty", summary.get("wrong_step_logs"), []))
    add(_expect("zero_summary_candidate_tensor_hash_count", summary.get("candidate_tensor_hash_count"), EXPECTED_RECORDS))
    add(_expect("zero_summary_path_signature_count", summary.get("path_signature_count"), EXPECTED_LOG_COUNT))
    add(_expect("zero_summary_record_identity_hash_count", summary.get("record_identity_hash_count"), EXPECTED_RECORDS))
    add(_expect("zero_summary_formal_seed_intersection_empty", summary.get("formal_seed_intersection"), []))
    add(_expect("zero_summary_tensor_hash_mismatches_zero", summary.get("tensor_hash_mismatches"), 0))
    add(_expect("zero_summary_executed_non_top1_zero", summary.get("executed_non_top1"), 0))
    add(_expect("zero_summary_default_off_missing_zero", summary.get("default_off_missing"), 0))
    add(_expect("zero_summary_provenance_missing_zero", summary.get("provenance_missing"), 0))
    add(_expect("zero_summary_closed_loop_collect_count_zero", summary.get("closed_loop_collect_count"), 0))
    add(_expect("zero_summary_forbidden_runtime_flags_zero", summary.get("forbidden_runtime_flags"), 0))
    for name in (
        "candidate_tensor_hash_intersection_count",
        "path_signature_intersection_count",
        "record_identity_intersection_count",
        "split_manifest_root_intersection_count",
    ):
        add(_expect(name, intersections.get(name), 0))
    add(_expect("training_data_contract_passed", training_contract.get("passed"), True))
    add(_expect("training_data_contract_records", training_contract.get("records"), EXPECTED_RECORDS))
    add(_expect("training_data_contract_failed_records_empty", training_contract.get("failed_records"), []))
    add(
        _expect(
            "training_input_contract_satisfied",
            training_contract.get("future_training_input_contract_satisfied"),
            True,
        )
    )
    add(_expect("training_contract_did_not_execute_replay", training_contract.get("replay_executed"), False))
    add(_expect("training_contract_did_not_generate_candidates", training_contract.get("candidate_generation_executed"), False))
    add(_expect("training_contract_did_not_authorize_training", training_contract.get("training_execution_authorized"), False))
    for log in selection_logs:
        add(_expect("selection_log_exists", log.is_file(), True))
        add(_expect("selection_log_under_execution_output_root", _is_relative_to(log.resolve(), execution_output_root), True))
    return checks


def _training_input_manifest(
    *,
    execution_output_root: Path,
    zero_overlap_artifact_dir: Path,
    output_dir: Path,
    selection_logs: list[Path],
    zero: dict[str, Any],
    training_contract: dict[str, Any],
    current_camp_head: str,
    current_dp_head: str,
) -> dict[str, Any]:
    return {
        "schema_version": TRAINING_INPUT_MANIFEST_SCHEMA_VERSION,
        "manifest_role": "v14_public_simulator_fixed_dp_candidate_training_input_manifest",
        "source_execution_output_root": str(execution_output_root),
        "source_zero_overlap_artifact_dir": str(zero_overlap_artifact_dir),
        "planned_output_dir": str(output_dir),
        "selection_logs": [str(path) for path in selection_logs],
        "expected_selection_log_count": EXPECTED_LOG_COUNT,
        "expected_steps_per_log": EXPECTED_STEPS_PER_LOG,
        "expected_records": EXPECTED_RECORDS,
        "expected_num_candidates": EXPECTED_NUM_CANDIDATES,
        "zero_overlap_intersections": zero["intersections"],
        "zero_overlap_registry_summary": zero["summary"],
        "training_data_contract": {
            "passed": training_contract.get("passed"),
            "records": training_contract.get("records"),
            "failed_record_count": len(training_contract.get("failed_records") or []),
            "future_training_input_contract_satisfied": training_contract.get(
                "future_training_input_contract_satisfied"
            ),
        },
        "fixed_dp_candidate_tensor_only": True,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
        "approved_atoms_nonnegative_simplex_only": True,
        "simplex_cvar_l2_master_convexity_preserved": True,
        "formal_seeds_11_12_13_excluded": True,
        "forbidden_operations": {
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "reference_blend": False,
            "guidance": False,
            "postprocess_or_postselection": False,
            "closed_loop_outcome_input": False,
            "dp_modification": False,
            "selector_promotion": False,
            "atom_promotion": False,
            "deployment": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_dp_head": current_dp_head,
            "required_dp_head": FIXED_DP_HEAD,
        },
    }


def _decision(
    *,
    passed: bool,
    failed: list[str],
    authorized_current_work: str,
    authorized_next_work: str,
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": bool(passed),
        "failed_checks": sorted(failed),
        "failure_class": None if passed else _failure_class(failed),
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if passed else None,
        "training_preflight_authorized_next": bool(passed),
        "training_execution_authorized_next": False,
        "data_preparation_executed": False,
        "fixed_dp_candidate_generation_executed_by_source": True,
        "zero_overlap_validation_executed_by_source": True,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "score_expression": SCORE_EXPRESSION,
        "approved_atoms_nonnegative_simplex_only": True,
        "simplex_cvar_l2_master_convexity_preserved": True,
    }


def _failure_class(failed: list[str]) -> str:
    if any("audit_" in check or "status_doc_" in check for check in failed):
        return "v14_eof_contract_mismatch"
    if any("zero_overlap" in check or "intersection_count" in check for check in failed):
        return "zero_overlap_source_contract_failure"
    if any("training_data_contract" in check or "training_input_contract" in check for check in failed):
        return "training_input_contract_failure"
    if any("head" in check or "dp_" in check for check in failed):
        return "head_or_fixed_dp_contract_failure"
    return "data_preparation_preflight_contract_failure"


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    contract = report["training_data_contract"]
    zero_summary = report["zero_overlap_summary"]
    return "\n".join(
        [
            "# V14 Public Simulator Fixed-DP Data-Preparation Preflight",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Selection logs: `{report['selection_log_count']}`",
            f"- Records: `{contract.get('records')}`",
            f"- Failed records: `{len(contract.get('failed_records') or [])}`",
            f"- Zero-overlap records: `{zero_summary.get('record_count')}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Training execution authorized next: `{decision['training_execution_authorized_next']}`",
            f"- Score expression: `{decision['score_expression']}`",
            "",
        ]
    )


def render_runbook(report: dict[str, Any]) -> str:
    manifest = report["planned_outputs"]["training_input_manifest_json"]
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "# Read-only v14 data-preparation preflight artifact.",
            "# This runbook intentionally does not train CAMP or modify DP.",
            f"test -f {json.dumps(manifest)}",
            f"echo v14_training_input_manifest={json.dumps(manifest)}",
            "",
        ]
    )


def _empty_contract() -> dict[str, Any]:
    return {
        "passed": False,
        "records": 0,
        "failed_records": [{"errors": ["selection_logs_missing"]}],
        "future_training_input_contract_satisfied": False,
        "replay_executed": False,
        "candidate_generation_executed": False,
        "training_execution_authorized": False,
    }


def _read_json(path: Path) -> Any:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    lines = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            lines.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _latest_value(text: str, key: str) -> str | None:
    prefix = f"{key}="
    matches = [line.split("=", 1)[1].strip() for line in text.splitlines() if line.startswith(prefix)]
    return matches[-1] if matches else None


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": observed == expected,
        "observed": observed,
        "expected": expected,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
