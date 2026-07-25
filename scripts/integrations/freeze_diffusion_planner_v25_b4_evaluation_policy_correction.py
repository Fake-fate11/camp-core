#!/usr/bin/env python3
"""Freeze the outcome-blind Fresh B4 evaluator-policy correction authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_b4_evaluation_policy_correction import (  # noqa: E402,E501
    CONTROLLER_ROOT_SHA256,
    CRITICAL_IMPLEMENTATION_MANIFEST_SHA256,
    EXECUTION_PLAN_SHA256,
    EXECUTION_REVIEW_ROOT_SHA256,
    EXECUTION_ROOT_SHA256,
    EXPERIMENT_PROTOCOL_SHA256,
    FIXED_DP_HEAD,
    HOLDOUT_IDENTITY_SHA256,
    IMPLEMENTATION_SOURCE_HEAD,
    OLD_CLOSEOUT_REVIEW_ROOT_SHA256,
    OLD_CLOSEOUT_ROOT_SHA256,
    OLD_CONTROL_COMMAND_SHA256,
    OLD_CONTROL_RUN_EXIT_SHA256,
    OLD_CONTROL_STDERR_SHA256,
    OLD_EVALUATION_ERROR,
    OLD_TERMINAL_HISTORY,
    OLD_TERMINAL_LEDGER_SHA256,
    OLD_TERMINAL_REASON,
    OPENING_RELEASE_ROOT_SHA256,
    POINTER_HEAD,
    POINTER_ONLY_PATHS,
    RUN_NONCE,
    correction_implementation_manifest,
    freeze_correction_authority,
    verify_release_dual_head_contract,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (  # noqa: E402
    _strict_canonical_json,
    canonical_json_bytes,
)
from camp_core.integrations.diffusion_planner_v25_holdout_opening_rc import (  # noqa: E402
    validate_production_rc_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_holdout_state import (  # noqa: E402
    validate_scientific_ledger,
)


def freeze(
    *,
    controller_decision_artifact: Path,
    controller_decision_root_sha256: str,
    opening_release_artifact: Path,
    opening_release_root_sha256: str,
    execution_artifact: Path,
    execution_root_sha256: str,
    execution_review_artifact: Path,
    execution_review_root_sha256: str,
    old_closeout_artifact: Path,
    old_closeout_root_sha256: str,
    old_closeout_review_artifact: Path,
    old_closeout_review_root_sha256: str,
    old_evaluation_control_dir: Path,
    scientific_ledger_path: Path,
    focused_tests_artifact: Path,
    focused_tests_root_sha256: str,
    fixed_dp_repo: Path,
    continuation_cas_namespace: Path,
    continuation_identity_slot_namespace: Path,
    output_dir: Path,
) -> str:
    output = Path(output_dir).resolve()
    head = _git_head(ROOT)
    expected_output = Path(
        "/root/autodl-tmp/"
        "camp_dp_v25_fresh_b4_evaluation_policy_correction_authority_"
        f"{head[:8]}_8680c1b19ce0620b"
    )
    if output != expected_output or output.exists():
        raise ValueError("Fresh B4 correction authority output drifted")
    if _tracked_changes(ROOT):
        raise ValueError("Fresh B4 correction repository is dirty")
    fixed = Path(fixed_dp_repo).resolve()
    if _git_head(fixed) != FIXED_DP_HEAD or _tracked_changes(fixed):
        raise ValueError("Fresh B4 fixed-DP authority drifted")
    bindings = (
        ("controller", controller_decision_artifact, controller_decision_root_sha256, CONTROLLER_ROOT_SHA256),
        ("opening release", opening_release_artifact, opening_release_root_sha256, OPENING_RELEASE_ROOT_SHA256),
        ("execution", execution_artifact, execution_root_sha256, EXECUTION_ROOT_SHA256),
        ("execution review", execution_review_artifact, execution_review_root_sha256, EXECUTION_REVIEW_ROOT_SHA256),
        ("old closeout", old_closeout_artifact, old_closeout_root_sha256, OLD_CLOSEOUT_ROOT_SHA256),
        ("old closeout review", old_closeout_review_artifact, old_closeout_review_root_sha256, OLD_CLOSEOUT_REVIEW_ROOT_SHA256),
        ("focused tests", focused_tests_artifact, focused_tests_root_sha256, focused_tests_root_sha256),
    )
    for label, raw_path, root, expected_root in bindings:
        path = Path(raw_path).resolve()
        if root != expected_root:
            raise ValueError(f"Fresh B4 {label} root drifted")
        verify_complete_seal(path, root, label=f"Fresh B4 {label}")
        if (path / "run.exit").read_bytes() != b"0\n":
            raise ValueError(f"Fresh B4 {label} did not pass")
    release_path = Path(opening_release_artifact).resolve()
    execution_path = Path(execution_artifact).resolve()
    execution_review_path = Path(execution_review_artifact).resolve()
    release = validate_production_rc_opening_release(
        _canonical_json(release_path / "decision.json")
    )
    dual_head = verify_release_dual_head_contract(
        ROOT,
        release=release,
        execution_heads=_heads(execution_path / "HEADS"),
        execution_review_heads=_heads(execution_review_path / "HEADS"),
    )
    review_report = _canonical_json(execution_review_path / "report.json")
    independent_review = review_report.get("independent_execution_review")
    if (
        release["holdout_identity"]["holdout_identity_sha256"]
        != HOLDOUT_IDENTITY_SHA256
        or release["experiment_protocol"]["experiment_protocol_sha256"]
        != EXPERIMENT_PROTOCOL_SHA256
        or release["holdout_identity"]["execution_plan_sha256"]
        != EXECUTION_PLAN_SHA256
        or release["run_nonce"] != RUN_NONCE
        or release["controller_decision_root_sha256"] != CONTROLLER_ROOT_SHA256
        or dual_head["critical_implementation_manifest_sha256"]
        != CRITICAL_IMPLEMENTATION_MANIFEST_SHA256
        or review_report.get("reviewed_root_sha256") != EXECUTION_ROOT_SHA256
        or type(independent_review) is not dict
        or independent_review.get("planned_pair_count") != 500
        or independent_review.get("reviewed_arm_run_count") != 1500
        or independent_review.get("complete_arm_run_count") != 1500
        or independent_review.get("all_complete_rows_reprojected") is not True
        or review_report.get("full_denominator_formed") is not True
    ):
        raise ValueError("Fresh B4 accepted denominator binding drifted")
    scientific_path = Path(scientific_ledger_path).resolve()
    scientific = validate_scientific_ledger(
        _strict_canonical_json(scientific_path)
    )
    if (
        _file_sha256(scientific_path) != OLD_TERMINAL_LEDGER_SHA256
        or scientific["state"] != "terminal_failure"
        or tuple(scientific["history"]) != OLD_TERMINAL_HISTORY
        or scientific["terminal_reason"] != OLD_TERMINAL_REASON
        or scientific["terminal_artifact_root_sha256"]
        != OLD_CLOSEOUT_ROOT_SHA256
    ):
        raise ValueError("Fresh B4 preserved terminal ledger drifted")
    control = Path(old_evaluation_control_dir).resolve()
    old_control = _old_control(control)
    correction_manifest = correction_implementation_manifest(ROOT)
    if correction_manifest["manifest_sha256"] == CRITICAL_IMPLEMENTATION_MANIFEST_SHA256:
        raise ValueError("Fresh B4 correction role manifest was not separated")
    focused = Path(focused_tests_artifact).resolve()
    focused_heads = _heads_any(focused / "HEADS")
    if head not in focused_heads.values():
        raise ValueError("Fresh B4 focused tests HEAD binding drifted")
    evaluation_dir = Path(
        "/root/autodl-tmp/"
        f"camp_dp_v25_fresh_b4_evaluation_corrected_{head[:8]}_8680c1b19ce0620b"
    )
    review_dir = Path(
        "/root/autodl-tmp/"
        f"camp_dp_v25_fresh_b4_evaluation_corrected_review_{head[:8]}_8680c1b19ce0620b"
    )
    if evaluation_dir.exists() or review_dir.exists():
        raise FileExistsError("Fresh B4 corrected evaluation output already exists")
    payload = freeze_correction_authority(
        holdout_identity_sha256=HOLDOUT_IDENTITY_SHA256,
        experiment_protocol_sha256=EXPERIMENT_PROTOCOL_SHA256,
        execution_plan_sha256=EXECUTION_PLAN_SHA256,
        run_nonce=RUN_NONCE,
        controller_decision=_binding(controller_decision_artifact, controller_decision_root_sha256),
        opening_release=_binding(opening_release_artifact, opening_release_root_sha256),
        execution=_binding(execution_artifact, execution_root_sha256),
        execution_review=_binding(execution_review_artifact, execution_review_root_sha256),
        implementation_source_head=IMPLEMENTATION_SOURCE_HEAD,
        pointer_head_at_release=POINTER_HEAD,
        pointer_only_changed_paths=POINTER_ONLY_PATHS,
        critical_implementation_manifest_sha256=CRITICAL_IMPLEMENTATION_MANIFEST_SHA256,
        old_evaluation_control=old_control,
        old_terminal_closeout=_binding(old_closeout_artifact, old_closeout_root_sha256),
        old_terminal_closeout_review=_binding(old_closeout_review_artifact, old_closeout_review_root_sha256),
        old_scientific_ledger={
            "path": str(scientific_path),
            "sha256": OLD_TERMINAL_LEDGER_SHA256,
            "state": scientific["state"],
            "history": scientific["history"],
            "terminal_reason": scientific["terminal_reason"],
            "terminal_artifact_root_sha256": scientific["terminal_artifact_root_sha256"],
        },
        correction_implementation={
            "head": head,
            "manifest_sha256": correction_manifest["manifest_sha256"],
            "manifest_paths": [row["path"] for row in correction_manifest["paths"]],
        },
        focused_tests=_binding(focused, focused_tests_root_sha256),
        corrected_evaluation_output_dir=str(evaluation_dir),
        corrected_evaluation_review_output_dir=str(review_dir),
        continuation_cas_namespace=str(Path(continuation_cas_namespace).resolve()),
        continuation_identity_slot_namespace=str(Path(continuation_identity_slot_namespace).resolve()),
    )
    return _write_atomic(output, payload)


def _old_control(control: Path) -> dict[str, Any]:
    run_sh = control / "run.sh"
    run_exit = control / "run.exit"
    stderr = control / "stderr.log"
    if (
        _file_sha256(run_sh) != OLD_CONTROL_COMMAND_SHA256
        or _file_sha256(run_exit) != OLD_CONTROL_RUN_EXIT_SHA256
        or _file_sha256(stderr) != OLD_CONTROL_STDERR_SHA256
        or run_exit.read_bytes() != b"1\n"
        or f"ValueError: {OLD_EVALUATION_ERROR}"
        not in stderr.read_text(encoding="utf-8")
    ):
        raise ValueError("Fresh B4 old evaluation control evidence drifted")
    return {
        "directory": str(control),
        "run_exit": 1,
        "error_type": "ValueError",
        "error_message": OLD_EVALUATION_ERROR,
        "command": _file_binding(run_sh),
        "run_exit_file": _file_binding(run_exit),
        "stderr": _file_binding(stderr),
    }


def _write_atomic(output: Path, payload: dict[str, Any]) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        (staging / "authority.json").write_bytes(canonical_json_bytes(payload))
        (staging / "HEADS").write_bytes(
            (
                f"correction_implementation_head={_git_head(ROOT)}\n"
                f"implementation_source_head={IMPLEMENTATION_SOURCE_HEAD}\n"
                f"pointer_head_at_release={POINTER_HEAD}\n"
                f"fixed_dp_head={FIXED_DP_HEAD}\n"
            ).encode("ascii")
        )
        (staging / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(staging, label="Fresh B4 evaluator-policy correction authority")
        os.rename(staging, output)
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _binding(path: Path, root: str) -> dict[str, str]:
    return {"path": str(Path(path).resolve()), "root_sha256": root}


def _file_binding(path: Path) -> dict[str, str]:
    return {"path": str(path), "sha256": _file_sha256(path)}


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(path: Path) -> dict[str, Any]:
    value = _strict_canonical_json(path)
    if type(value) is not dict:
        raise ValueError(f"Fresh B4 JSON object drifted: {path}")
    return value


def _heads(path: Path) -> dict[str, str]:
    value = _heads_any(path)
    if set(value) != {"camp_head", "fixed_dp_head"}:
        raise ValueError(f"Fresh B4 HEADS field set drifted: {path}")
    return value


def _heads_any(path: Path) -> dict[str, str]:
    text = Path(path).read_text(encoding="ascii")
    if not text.endswith("\n") or "\r" in text:
        raise ValueError(f"Fresh B4 HEADS bytes drifted: {path}")
    result: dict[str, str] = {}
    for line in text[:-1].split("\n"):
        if line.count("=") != 1:
            raise ValueError(f"Fresh B4 HEADS row drifted: {path}")
        key, value = line.split("=", 1)
        if key in result:
            raise ValueError(f"duplicate Fresh B4 HEADS row: {key}")
        result[key] = value
    return result


def _git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(Path(repo).resolve()), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def _tracked_changes(repo: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "-C", str(Path(repo).resolve()), "status", "--porcelain", "--untracked-files=no"],
            text=True,
        ).strip()
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "controller-decision",
        "opening-release",
        "execution",
        "execution-review",
        "old-closeout",
        "old-closeout-review",
        "focused-tests",
    ):
        parser.add_argument(f"--{name}-artifact", type=Path, required=True)
        parser.add_argument(f"--{name}-root-sha256", required=True)
    parser.add_argument("--old-evaluation-control-dir", type=Path, required=True)
    parser.add_argument("--scientific-ledger-path", type=Path, required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--continuation-cas-namespace", type=Path, required=True)
    parser.add_argument("--continuation-identity-slot-namespace", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    root = freeze(**vars(_arguments()))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
