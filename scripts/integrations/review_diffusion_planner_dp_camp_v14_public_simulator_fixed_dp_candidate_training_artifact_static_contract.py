#!/usr/bin/env python3
"""V14 fixed-DP CAMP training artifact static contract review.

This gate reviews an already-produced training artifact. It does not train,
run replay, generate candidates, modify DP, promote artifacts, deploy, or make
safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension  # noqa: E402


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SCHEMA_VERSION = (
    "dp_camp_v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_v1"
)
EXPECTED_CURRENT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_training_execution_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_training_artifact_static_contract_review"
)
AUTHORIZED_NEXT_WORK = (
    "public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_preflight"
)
READY_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_training_artifact_static_contract_review_passed"
)
REJECT_STATUS = (
    "public_simulator_fixed_dp_candidate_generation_training_artifact_static_contract_review_rejected"
)
EXPECTED_TRAINING_TYPE = "diffusion_planner_static_candidate_preference"
EXPECTED_LABEL_SOURCE = "dp_reward"
EXPECTED_REWARD_KEY = "quality_without_progress"
EXPECTED_REWARD_PROGRESS_WEIGHT = 2.0
EXPECTED_RECORDS_USED = 2914
EXPECTED_DROPPED_RECORDS = 286
EXPECTED_CONTRACT_RECORDS = 3200
EXPECTED_NUM_CANDIDATES = 8
EXPECTED_NUM_ATOMS = 9
EXPECTED_OUTPUT_FILES = (
    "atom_scales_dp_static.json",
    "offline_weights_dp_static.npy",
    "training_summary.json",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training_execution_artifact_dir", type=Path, required=True)
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
        training_execution_artifact_dir=args.training_execution_artifact_dir,
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
    training_execution_artifact_dir: Path,
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
    artifact_dir = training_execution_artifact_dir.resolve()
    output_dir = output_dir.resolve()
    summary_path = artifact_dir / "training_summary.json"
    scales_path = artifact_dir / "atom_scales_dp_static.json"
    weights_path = artifact_dir / "offline_weights_dp_static.npy"
    summary = _read_json_dict(summary_path)
    scales_payload = _read_json_dict(scales_path)
    weights = _read_weights(weights_path)
    heads = _parse_key_values(_read_text(artifact_dir / "HEADS"))
    sha256s = _read_sha256sums(artifact_dir / "SHA256SUMS")
    output_files = _read_lines(artifact_dir / "planned_output_files.txt")
    v14_text = _read_text(v14_audit_md)
    status_text = _read_text(current_status_md)
    review = _review_summary(
        summary=summary,
        scales_payload=scales_payload,
        weights=weights,
        output_files=output_files,
    )
    checks = _checks(
        artifact_dir=artifact_dir,
        summary_path=summary_path,
        scales_path=scales_path,
        weights_path=weights_path,
        heads=heads,
        sha256s=sha256s,
        output_files=output_files,
        summary=summary,
        scales_payload=scales_payload,
        weights=weights,
        review=review,
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
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "training_artifact_static_review_only": True,
            "training_executed_by_source": True,
            "training_executed_by_review": False,
            "replay_executed": False,
            "candidate_generation_executed": False,
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
            "deployable_checkpoint_claim": False,
            "safety_benefit_claim": False,
            "camp_over_dp_top1_claim": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
            "approved_atoms_nonnegative_simplex_only": True,
            "simplex_cvar_l2_master_convexity_preserved": True,
        },
        "inputs": {
            "training_execution_artifact_dir": str(artifact_dir),
            "v14_audit_md": str(v14_audit_md.resolve()),
            "current_status_md": str(current_status_md.resolve()),
            "output_dir": str(output_dir),
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
            "artifact_camp_head": heads.get("CAMP_HEAD"),
            "artifact_camp_origin_main": heads.get("CAMP_ORIGIN_MAIN"),
            "artifact_dp_head": heads.get("DP_HEAD"),
        },
        "artifact_hashes": sha256s,
        "training_summary": summary,
        "artifact_review": review,
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
    _write_json(output_dir / "training_artifact_static_contract_report.json", report)
    (output_dir / "training_artifact_static_contract_report.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    _write_sha256sums(output_dir)


def _checks(
    *,
    artifact_dir: Path,
    summary_path: Path,
    scales_path: Path,
    weights_path: Path,
    heads: dict[str, str],
    sha256s: dict[str, str],
    output_files: list[str],
    summary: dict[str, Any],
    scales_payload: dict[str, Any],
    weights: np.ndarray,
    review: dict[str, Any],
    v14_text: str,
    status_text: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    expected_atom_schema, expected_atom_names = atom_schema_for_dimension(
        EXPECTED_NUM_ATOMS
    )
    contract = _dict(summary.get("dp_native_training_data_contract"))
    return [
        _expect("artifact_dir_exists", artifact_dir.is_dir(), True),
        _expect("training_summary_exists", summary_path.is_file(), True),
        _expect("atom_scales_exists", scales_path.is_file(), True),
        _expect("offline_weights_exists", weights_path.is_file(), True),
        _expect("heads_exists", (artifact_dir / "HEADS").is_file(), True),
        _expect("sha256sums_exists", (artifact_dir / "SHA256SUMS").is_file(), True),
        _expect("exit_code", _read_text(artifact_dir / "exit.code").strip(), "0"),
        _expect("audit_latest_status", _latest_value(v14_text, "current_v14_status"), EXPECTED_CURRENT_STATUS),
        _expect("audit_latest_next_work", _latest_value(v14_text, "next_work_target"), authorized_current_work),
        _expect("status_doc_current_status", EXPECTED_CURRENT_STATUS in status_text, True),
        _expect("status_doc_next_work", authorized_current_work in status_text, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("artifact_dp_head_fixed", heads.get("DP_HEAD"), FIXED_DP_HEAD),
        _expect("artifact_camp_head_matches_origin", heads.get("CAMP_HEAD"), heads.get("CAMP_ORIGIN_MAIN")),
        _expect("training_type", summary.get("training_type"), EXPECTED_TRAINING_TYPE),
        _expect("label_source", summary.get("label_source"), EXPECTED_LABEL_SOURCE),
        _expect("reward_key", summary.get("reward_key"), EXPECTED_REWARD_KEY),
        _expect("reward_progress_weight", _safe_float(summary.get("reward_progress_weight")), EXPECTED_REWARD_PROGRESS_WEIGHT),
        _expect("num_records", summary.get("num_records"), EXPECTED_RECORDS_USED),
        _expect("dropped_records_without_feasible_candidate", summary.get("dropped_records_without_feasible_candidate"), EXPECTED_DROPPED_RECORDS),
        _expect("num_candidates", summary.get("num_candidates"), EXPECTED_NUM_CANDIDATES),
        _expect("num_atoms", summary.get("num_atoms"), EXPECTED_NUM_ATOMS),
        _expect("atom_schema_version", summary.get("atom_schema_version"), expected_atom_schema),
        _expect("atom_names", tuple(summary.get("atom_names") or ()), tuple(expected_atom_names)),
        _expect("contract_records", contract.get("records"), EXPECTED_CONTRACT_RECORDS),
        _expect("contract_failed_records_zero", len(contract.get("failed_records", [])), 0),
        _expect("contract_future_training_input", contract.get("future_training_input_contract_satisfied"), True),
        _expect("contract_candidate_generation_executed_false", contract.get("candidate_generation_executed"), False),
        _expect("contract_dp_modification_false", contract.get("dp_modification_authorized"), False),
        _expect("contract_safety_claim_false", contract.get("safety_benefit_claim_authorized"), False),
        _expect("contract_camp_over_dp_claim_false", contract.get("camp_over_dp_top1_claim_authorized"), False),
        _expect("closed_loop_outcome_key_absent", summary.get("outcome_key"), None),
        _expect("outcome_weights_path_absent", summary.get("outcome_weights_path"), None),
        _expect("outcome_weights_absent", summary.get("outcome_weights"), None),
        _expect("proxy_weights_absent", summary.get("proxy_weights_normalized"), None),
        _expect("output_files", tuple(output_files), EXPECTED_OUTPUT_FILES),
        _expect("weights_length", review["weights_length"], EXPECTED_NUM_ATOMS),
        _expect("weights_all_finite", review["weights_all_finite"], True),
        _expect("weights_nonnegative", review["weights_nonnegative"], True),
        _check("weights_sum_one", abs(review["weights_sum"] - 1.0) <= 1e-9, review["weights_sum"], "1.0 +/- 1e-9"),
        _expect("weights_file_matches_summary", review["weights_file_matches_summary"], True),
        _expect("scales_schema", scales_payload.get("atom_schema_version"), expected_atom_schema),
        _expect("scales_names", tuple(scales_payload.get("atom_names") or ()), tuple(expected_atom_names)),
        _expect("scales_length", review["scales_length"], EXPECTED_NUM_ATOMS),
        _expect("scales_all_positive_finite", review["scales_all_positive_finite"], True),
        _expect("training_summary_sha256_matches", sha256s.get("training_summary.json"), _sha256(summary_path) if summary_path.is_file() else None),
        _expect("atom_scales_sha256_matches", sha256s.get("atom_scales_dp_static.json"), _sha256(scales_path) if scales_path.is_file() else None),
        _expect("offline_weights_sha256_matches", sha256s.get("offline_weights_dp_static.npy"), _sha256(weights_path) if weights_path.is_file() else None),
    ]


def _review_summary(
    *,
    summary: dict[str, Any],
    scales_payload: dict[str, Any],
    weights: np.ndarray,
    output_files: list[str],
) -> dict[str, Any]:
    summary_weights = np.asarray(summary.get("trained_weights") or [], dtype=np.float64)
    scales = np.asarray(scales_payload.get("scales") or [], dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64).reshape(-1)
    return {
        "output_files": output_files,
        "weights_length": int(weights.size),
        "weights_sum": float(np.sum(weights)) if weights.size else math.nan,
        "weights_min": float(np.min(weights)) if weights.size else math.nan,
        "weights_max": float(np.max(weights)) if weights.size else math.nan,
        "weights_all_finite": bool(weights.size and np.all(np.isfinite(weights))),
        "weights_nonnegative": bool(weights.size and np.all(weights >= 0.0)),
        "weights_file_matches_summary": bool(
            weights.shape == summary_weights.shape
            and weights.size
            and np.allclose(weights, summary_weights, rtol=0.0, atol=1e-12)
        ),
        "scales_length": int(scales.size),
        "scales_all_positive_finite": bool(
            scales.size and np.all(np.isfinite(scales)) and np.all(scales > 0.0)
        ),
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
        "training_artifact_static_contract_review_complete": bool(passed),
        "trained_default_off_shadow_replay_evaluation_preflight_authorized_next": bool(passed),
        "training_executed_by_source": True,
        "training_executed_by_review": False,
        "replay_executed": False,
        "candidate_generation_executed": False,
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
    if any("head" in check or "dp_" in check for check in failed):
        return "head_or_fixed_dp_contract_failure"
    if any("weights" in check or "scales" in check or "atom_" in check for check in failed):
        return "training_artifact_weight_or_atom_contract_failure"
    if any("label" in check or "outcome" in check or "reward" in check for check in failed):
        return "training_label_contract_failure"
    return "training_artifact_static_contract_failure"


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    review = report["artifact_review"]
    summary = report["training_summary"]
    return "\n".join(
        [
            "# V14 Fixed-DP CAMP Training Artifact Static Contract Review",
            "",
            f"- Status: `{decision['status']}`",
            f"- Passed: `{decision['passed']}`",
            f"- Failed checks: `{decision['failed_checks']}`",
            f"- Authorized next work: `{decision['authorized_next_work']}`",
            f"- Records used: `{summary.get('num_records')}`",
            f"- Dropped all-infeasible records: `{summary.get('dropped_records_without_feasible_candidate')}`",
            f"- Atom schema: `{summary.get('atom_schema_version')}`",
            f"- Weights sum: `{review['weights_sum']}`",
            f"- Weights min/max: `{review['weights_min']}` / `{review['weights_max']}`",
            "",
            "This is a static artifact review only. It does not run replay, "
            "generate candidates, modify DP, promote, deploy, or make "
            "safety/CAMP-over-DP claims.",
            "",
        ]
    )


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _read_weights(path: Path) -> np.ndarray:
    if not path.is_file():
        return np.asarray([], dtype=np.float64)
    return np.asarray(np.load(path), dtype=np.float64).reshape(-1)


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _read_sha256sums(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in _read_text(path).splitlines():
        parts = line.split()
        if len(parts) >= 2:
            result[parts[-1]] = parts[0]
    return result


def _read_lines(path: Path) -> list[str]:
    return [line.strip() for line in _read_text(path).splitlines() if line.strip()]


def _parse_key_values(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path) -> None:
    lines = []
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            lines.append(f"{_sha256(path)}  {path.name}")
    (output_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
