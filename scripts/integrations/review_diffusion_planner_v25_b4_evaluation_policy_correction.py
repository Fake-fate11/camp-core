#!/usr/bin/env python3
"""Independently review the Fresh B4 evaluator-policy correction authority."""

from __future__ import annotations

import argparse
import ast
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
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (  # noqa: E402
    _strict_canonical_json,
    canonical_json_bytes,
    canonical_sha256,
)


SOURCE = "7be93df20deee03587b9898e8560909662df972c"
POINTER = "06d3a1f3a37061f93f5c9788312ae59d1356d126"
FIXED_DP = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
IDENTITY = "5f2f8e2c2eb90927ec485a8d0baa3935b155e82d90b04fa3d456fc845cd8464a"
PROTOCOL = "aa79576f8ac487e2ce197c481d57f9c5d350a41d9522096975786207ef76785f"
PLAN = "41442dd7d71552972d737d9a9e3d56e9827f864e0c06e11c57487f651206dee0"
NONCE = "8680c1b19ce0620b7dc2ec9453ffde0da024d3443e6d6307fc41e87f3dad3b42"
CONTROLLER_ROOT = "06f2bf198b9983e0e15f9e0feaba52bc0d595fdd5703d73d98e21c1e8c4f08a2"
RELEASE_ROOT = "7deec7b81a1ad20dd9eb4657c0c3066ce695bc797349def843c0e7152f85851b"
EXECUTION_ROOT = "e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881"
EXECUTION_REVIEW_ROOT = "f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d"
CLOSEOUT_ROOT = "a97af4901ac0627ece1203eaac130f8bf2f10caf6b8bee523555582b2ff3d398"
CLOSEOUT_REVIEW_ROOT = "86aa7ca12ae8cfa4a655fc55022761a78ac54a3a22ef32a750df9c7eb75d0062"
OLD_LEDGER_SHA = "c3db4fb56f28efda7e3feb762ab0f01954f09983813b442f0a31e7730fbe72e4"
OLD_CONTROL_SHAS = {
    "command": "5c2134847ef9a1686d3653d48d0147912ee5abc713cf15f574dc5ec02cc0e304",
    "run_exit_file": "4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865",
    "stderr": "23ffd85aa1c6abf6c04a4bef15469fdd83a1e05a01f53aadbc6d5a4a3a1d8a60",
}
CRITICAL_MANIFEST = "f3b707d480b30e1d37d2c10355d8a824df4cff8230af7d78d803dd4504ef6c2b"
POINTER_PATHS = (
    "camp_core/tests/test_diffusion_planner_v25_iteration_audit.py",
    "docs/diffusion_planner_current_status.md",
    "docs/diffusion_planner_v25_iteration_audit.md",
)
CORRECTION_PATHS = (
    "camp_core/camp_core/integrations/diffusion_planner_v25_b4_evaluation_policy_correction.py",
    "camp_core/camp_core/integrations/diffusion_planner_v25_b4_evaluation_continuation.py",
    "scripts/integrations/evaluate_diffusion_planner_v25_holdout.py",
    "scripts/integrations/review_diffusion_planner_v25_holdout_evaluation.py",
    "scripts/integrations/freeze_diffusion_planner_v25_b4_evaluation_policy_correction.py",
    "scripts/integrations/review_diffusion_planner_v25_b4_evaluation_policy_correction.py",
    "scripts/integrations/authorize_diffusion_planner_v25_b4_evaluation_continuation.py",
)
AUTHORITY_FIELDS = frozenset(
    {
        "schema_version", "status", "benchmark", "phase",
        "user_override_date", "user_override_decision",
        "holdout_identity_sha256", "experiment_protocol_sha256",
        "execution_plan_sha256", "run_nonce", "controller_decision",
        "opening_release", "execution", "execution_review",
        "implementation_source_head", "pointer_head_at_release",
        "pointer_only_changed_paths", "critical_implementation_manifest_sha256",
        "fixed_dp_head", "old_evaluation_control", "old_terminal_closeout",
        "old_terminal_closeout_review", "old_scientific_ledger",
        "correction_implementation", "focused_tests",
        "corrected_evaluation_output_dir", "corrected_evaluation_review_output_dir",
        "continuation", "fresh_execution_reused", "fresh_execution_rerun",
        "raw_outcome_inspected_before_authority", "scientific_contract_changed",
        "old_terminal_diagnostic_preserved", "new_fresh_authorized",
        "promotion_deployment_activation_authorized", "next_authority",
        "authority_payload_sha256",
    }
)


def review(
    *,
    authority_artifact: Path,
    authority_root_sha256: str,
    output_dir: Path,
) -> str:
    source = Path(authority_artifact).resolve()
    output = Path(output_dir).resolve()
    head = _git_head()
    expected_authority = Path(
        "/root/autodl-tmp/"
        f"camp_dp_v25_fresh_b4_evaluation_policy_correction_authority_{head[:8]}_8680c1b19ce0620b"
    )
    expected_output = Path(
        "/root/autodl-tmp/"
        f"camp_dp_v25_fresh_b4_evaluation_policy_correction_authority_review_{head[:8]}_8680c1b19ce0620b"
    )
    if source != expected_authority or output != expected_output or output.exists():
        raise ValueError("Fresh B4 correction review exact directory drifted")
    if _tracked_changes():
        raise ValueError("Fresh B4 correction reviewer worktree is dirty")
    verify_complete_seal(source, authority_root_sha256, label="Fresh B4 correction authority")
    if (source / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh B4 correction authority did not pass")
    authority = _object(source / "authority.json")
    if set(authority) != AUTHORITY_FIELDS:
        raise ValueError("Fresh B4 correction authority field set drifted")
    unsigned = dict(authority)
    payload_sha = unsigned.pop("authority_payload_sha256", None)
    if payload_sha != canonical_sha256(unsigned):
        raise ValueError("Fresh B4 correction authority payload SHA drifted")
    exact = {
        "holdout_identity_sha256": IDENTITY,
        "experiment_protocol_sha256": PROTOCOL,
        "execution_plan_sha256": PLAN,
        "run_nonce": NONCE,
        "implementation_source_head": SOURCE,
        "pointer_head_at_release": POINTER,
        "critical_implementation_manifest_sha256": CRITICAL_MANIFEST,
        "fixed_dp_head": FIXED_DP,
        "fresh_execution_reused": True,
        "fresh_execution_rerun": False,
        "raw_outcome_inspected_before_authority": False,
        "scientific_contract_changed": False,
        "old_terminal_diagnostic_preserved": True,
        "new_fresh_authorized": False,
        "promotion_deployment_activation_authorized": False,
    }
    if any(authority.get(key) != value for key, value in exact.items()):
        raise ValueError("Fresh B4 correction authority literal binding drifted")
    if tuple(authority["pointer_only_changed_paths"]) != POINTER_PATHS:
        raise ValueError("Fresh B4 correction pointer allowlist drifted")
    roots = {
        "controller_decision": CONTROLLER_ROOT,
        "opening_release": RELEASE_ROOT,
        "execution": EXECUTION_ROOT,
        "execution_review": EXECUTION_REVIEW_ROOT,
        "old_terminal_closeout": CLOSEOUT_ROOT,
        "old_terminal_closeout_review": CLOSEOUT_REVIEW_ROOT,
    }
    for name, expected_root in roots.items():
        binding = authority[name]
        if set(binding) != {"path", "root_sha256"} or binding["root_sha256"] != expected_root:
            raise ValueError(f"Fresh B4 correction {name} binding drifted")
        path = Path(binding["path"]).resolve()
        verify_complete_seal(path, expected_root, label=f"Fresh B4 {name}")
        if (path / "run.exit").read_bytes() != b"0\n":
            raise ValueError(f"Fresh B4 {name} did not pass")
    changed = tuple(
        subprocess.check_output(
            ["git", "-C", str(ROOT), "diff", "--name-only", SOURCE, POINTER, "--"],
            text=True,
        ).splitlines()
    )
    if changed != POINTER_PATHS or _historical_manifest_sha() != CRITICAL_MANIFEST:
        raise ValueError("Fresh B4 correction historical dual-HEAD proof drifted")
    old_control = authority["old_evaluation_control"]
    for name, expected_sha in OLD_CONTROL_SHAS.items():
        binding = old_control[name]
        if _file_sha256(Path(binding["path"])) != expected_sha or binding["sha256"] != expected_sha:
            raise ValueError("Fresh B4 old control evidence SHA drifted")
    old_ledger = authority["old_scientific_ledger"]
    if (
        _file_sha256(Path(old_ledger["path"])) != OLD_LEDGER_SHA
        or old_ledger
        != {
            "path": old_ledger["path"],
            "sha256": OLD_LEDGER_SHA,
            "state": "terminal_failure",
            "history": ["exposure_started", "full_denominator_formed", "terminal_failure"],
            "terminal_reason": "post_exposure_evaluation_control_fatal",
            "terminal_artifact_root_sha256": CLOSEOUT_ROOT,
        }
    ):
        raise ValueError("Fresh B4 preserved terminal ledger drifted")
    correction = authority["correction_implementation"]
    if (
        correction["head"] != head
        or correction["manifest_paths"] != list(CORRECTION_PATHS)
        or correction["manifest_sha256"] != _correction_manifest_sha()
    ):
        raise ValueError("Fresh B4 correction implementation manifest drifted")
    focused = authority["focused_tests"]
    verify_complete_seal(Path(focused["path"]), focused["root_sha256"], label="Fresh B4 correction focused tests")
    if (Path(focused["path"]) / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh B4 correction focused tests did not pass")
    evaluation_dir = Path(authority["corrected_evaluation_output_dir"])
    evaluation_review_dir = Path(authority["corrected_evaluation_review_output_dir"])
    if evaluation_dir.exists() or evaluation_review_dir.exists():
        raise FileExistsError("Fresh B4 corrected output already exists")
    continuation = authority["continuation"]
    cas = Path(continuation["cas_namespace"])
    slot = Path(continuation["identity_slot_namespace"])
    if cas.exists() and any(cas.iterdir()):
        raise FileExistsError("Fresh B4 continuation CAS is not empty")
    if slot.exists() and any(slot.iterdir()):
        raise FileExistsError("Fresh B4 continuation identity slot is not empty")
    report = {
        "schema_version": "camp_dp_v25_fresh_b4_evaluator_policy_correction_authority_review_v1",
        "status": "passed_independent_fresh_b4_evaluator_policy_correction_authority_review",
        "reviewed_authority": {"path": str(source), "root_sha256": authority_root_sha256},
        "holdout_identity_sha256": IDENTITY,
        "experiment_protocol_sha256": PROTOCOL,
        "execution_plan_sha256": PLAN,
        "run_nonce": NONCE,
        "implementation_source_head": SOURCE,
        "pointer_head_at_release": POINTER,
        "pointer_only_changed_paths": list(POINTER_PATHS),
        "critical_implementation_manifest_sha256": CRITICAL_MANIFEST,
        "fixed_dp_head": FIXED_DP,
        "old_terminal_ledger_sha256": OLD_LEDGER_SHA,
        "old_terminal_state": "terminal_failure",
        "old_terminal_history": ["exposure_started", "full_denominator_formed", "terminal_failure"],
        "old_terminal_reason": "post_exposure_evaluation_control_fatal",
        "old_terminal_artifact_root_sha256": CLOSEOUT_ROOT,
        "correction_implementation_head": head,
        "correction_implementation_manifest_sha256": correction["manifest_sha256"],
        "focused_test_root_sha256": focused["root_sha256"],
        "corrected_evaluation_output_dir": str(evaluation_dir),
        "corrected_evaluation_review_output_dir": str(evaluation_review_dir),
        "continuation": continuation,
        "accepted_roots_independently_verified": True,
        "old_diagnostic_independently_verified": True,
        "corrected_output_dirs_absent": True,
        "second_authority_or_evaluation_absent": True,
        "raw_outcome_values_inspected": False,
        "fresh_execution_rerun": False,
        "scientific_contract_changed": False,
        "promotion_deployment_activation_authorized": False,
    }
    return _write_atomic(output, report)


def _historical_manifest_sha() -> str:
    relative = "camp_core/camp_core/integrations/diffusion_planner_v25_fresh_preopen_authority.py"
    text = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{SOURCE}:{relative}"], text=True)
    paths = None
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "TRACKED_AUTHORITY_FILES":
            paths = ast.literal_eval(node.value)
            break
    if type(paths) is not tuple or any(type(item) is not str for item in paths):
        raise ValueError("Fresh B4 reviewer historical path oracle drifted")
    rows = []
    for path in paths:
        blob = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{SOURCE}:{path}"])
        rows.append({"path": path, "sha256": hashlib.sha256(blob).hexdigest()})
    return hashlib.sha256(canonical_json_bytes(rows)).hexdigest()


def _correction_manifest_sha() -> str:
    rows = [{"path": path, "sha256": _file_sha256(ROOT / path)} for path in CORRECTION_PATHS]
    return hashlib.sha256(canonical_json_bytes(rows)).hexdigest()


def _object(path: Path) -> dict[str, Any]:
    value = _strict_canonical_json(path)
    if type(value) is not dict:
        raise ValueError(f"Fresh B4 JSON object drifted: {path}")
    return value


def _write_atomic(output: Path, report: dict[str, Any]) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        (staging / "report.json").write_bytes(canonical_json_bytes(report))
        (staging / "HEADS").write_bytes(
            (
                f"correction_implementation_head={_git_head()}\n"
                f"implementation_source_head={SOURCE}\n"
                f"pointer_head_at_release={POINTER}\n"
                f"fixed_dp_head={FIXED_DP}\n"
            ).encode("ascii")
        )
        (staging / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(staging, label="independent Fresh B4 correction authority review")
        os.rename(staging, output)
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def _tracked_changes() -> bool:
    return bool(subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"], text=True).strip())


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority-artifact", type=Path, required=True)
    parser.add_argument("--authority-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    root = review(**vars(_arguments()))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
