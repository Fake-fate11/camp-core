#!/usr/bin/env python3
"""Independently review the outcome-blind Fresh B4 evaluation closeout."""

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
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (  # noqa: E402,E501
    _strict_canonical_json,
    canonical_json_bytes,
    canonical_sha256,
    strict_equal,
)
from camp_core.integrations.diffusion_planner_v25_holdout_opening_rc import (  # noqa: E402,E501
    validate_production_rc_controller_decision,
    validate_production_rc_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_holdout_state import (  # noqa: E402
    validate_scientific_ledger,
)


SCHEMA_VERSION = (
    "camp_dp_v25_fresh_b4_post_exposure_evaluation_control_fatal_closeout_v1"
)
REVIEW_SCHEMA_VERSION = (
    "camp_dp_v25_fresh_b4_post_exposure_evaluation_control_fatal_closeout_review_v1"
)
STATUS = "post_exposure_evaluation_control_fatal_honest_no_claim"
REVIEW_STATUS = (
    "passed_independent_fresh_b4_evaluation_terminal_closeout_review"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
ERROR_MESSAGE = "holdout execution/evaluation role HEAD drifted"
NEXT_AUTHORITY = "final_report_and_ultra_terminal_review_only"
UNAVAILABLE = "unavailable_due_to_post_exposure_evaluation_fatal"
_FIELDS = frozenset(
    {
        "schema_version",
        "status",
        "benchmark",
        "phase",
        "block_class",
        "error_type",
        "error_message",
        "holdout_identity_sha256",
        "experiment_protocol_sha256",
        "execution_plan_sha256",
        "run_nonce",
        "controller_decision",
        "opening_release",
        "execution",
        "execution_review",
        "evaluation_output_dir",
        "evaluation_control",
        "evaluation_artifact_created",
        "evaluation_root_sha256",
        "evaluation_review_output_dir",
        "evaluation_review_started",
        "evaluation_review_artifact_created",
        "related_process_count",
        "implementation_source_head",
        "pointer_head_at_release",
        "fixed_dp_head",
        "reporting_machinery_head",
        "scientific_ledger_before",
        "planned_pair_count",
        "complete_paired_row_count",
        "planned_arm_run_count",
        "complete_arm_run_count",
        "terminal_arm_run_count",
        "full_denominator_formed",
        "outcome_fields_consumed",
        "raw_outcome_values_inspected",
        "rerun_allowed",
        "new_nonce_allowed",
        "alternate_directory_allowed",
        "suffix_allowed",
        "claim_authorized",
        "evaluation_result_status",
        "next_authority",
        "closeout_payload_sha256",
    }
)
_CONTROL_FIELDS = frozenset(
    {
        "directory",
        "command",
        "command_receipt",
        "run_exit_file",
        "run_exit",
        "stderr",
    }
)


def review(
    *,
    source_artifact: Path,
    source_root_sha256: str,
    controller_decision_artifact: Path,
    controller_decision_root_sha256: str,
    opening_release_artifact: Path,
    opening_release_root_sha256: str,
    execution_artifact: Path,
    execution_root_sha256: str,
    execution_review_artifact: Path,
    execution_review_root_sha256: str,
    evaluation_output_dir: Path,
    evaluation_control_dir: Path,
    evaluation_review_output_dir: Path,
    scientific_ledger_path: Path,
    fixed_dp_repo: Path,
    output_dir: Path,
) -> str:
    source = Path(source_artifact).resolve()
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
    source_seal = verify_complete_seal(
        source, source_root_sha256, label="Fresh B4 evaluation terminal closeout"
    )
    if set(source_seal["manifest_paths"]) != {
        "COMMAND",
        "HEADS",
        "closeout.json",
        "run.exit",
    } or (source / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh B4 evaluation closeout inventory drifted")

    controller_path = Path(controller_decision_artifact).resolve()
    release_path = Path(opening_release_artifact).resolve()
    execution_path = Path(execution_artifact).resolve()
    execution_review_path = Path(execution_review_artifact).resolve()
    evaluation_path = Path(evaluation_output_dir).resolve()
    control_path = Path(evaluation_control_dir).resolve()
    evaluation_review_path = Path(evaluation_review_output_dir).resolve()
    scientific_path = Path(scientific_ledger_path).resolve()
    dp_repo = Path(fixed_dp_repo).resolve()

    for label, path, root in (
        (
            "Fresh B4 controller decision",
            controller_path,
            controller_decision_root_sha256,
        ),
        ("Fresh B4 opening release", release_path, opening_release_root_sha256),
        (
            "Fresh B4 execution review",
            execution_review_path,
            execution_review_root_sha256,
        ),
    ):
        verify_complete_seal(path, root, label=label)
    _verify_root_receipt(
        execution_path,
        execution_root_sha256,
        label="Fresh B4 execution",
    )
    if any(
        (path / "run.exit").read_bytes() != b"0\n"
        for path in (
            controller_path,
            release_path,
            execution_path,
            execution_review_path,
        )
    ):
        raise ValueError("Fresh B4 accepted artifact run.exit drifted")

    controller = validate_production_rc_controller_decision(
        _strict_canonical_json(controller_path / "decision.json")
    )
    release = validate_production_rc_opening_release(
        _strict_canonical_json(release_path / "decision.json")
    )
    execution_review_report = _strict_canonical_json(
        execution_review_path / "report.json"
    )
    independent = execution_review_report.get("independent_execution_review")
    if (
        controller["holdout_identity"] != release["holdout_identity"]
        or controller["experiment_protocol"] != release["experiment_protocol"]
        or release["controller_decision_root_sha256"]
        != controller_decision_root_sha256
        or release["fixed_dp_head"] != FIXED_DP_HEAD
        or execution_review_report.get("status")
        != "passed_independent_holdout_execution_review"
        or execution_review_report.get("reviewed_root_sha256")
        != execution_root_sha256
        or execution_review_report.get("opening_release_root_sha256")
        != opening_release_root_sha256
        or execution_review_report.get("full_denominator_formed") is not True
        or type(independent) is not dict
        or independent.get("planned_pair_count") != 500
        or independent.get("reviewed_arm_run_count") != 1500
        or independent.get("complete_arm_run_count") != 1500
    ):
        raise ValueError("Fresh B4 independent accepted chain drifted")
    if evaluation_path.exists() or evaluation_review_path.exists():
        raise ValueError("Fresh B4 evaluation terminal absence drifted")
    if _related_evaluation_processes(evaluation_path, evaluation_review_path):
        raise ValueError("Fresh B4 evaluation process still exists")

    scientific = validate_scientific_ledger(
        _strict_canonical_json(scientific_path)
    )
    evidence = _control_evidence(
        control_path,
        release_path=release_path,
        release_root=opening_release_root_sha256,
        execution_path=execution_path,
        execution_root=execution_root_sha256,
        execution_review_path=execution_review_path,
        execution_review_root=execution_review_root_sha256,
        evaluation_path=evaluation_path,
    )
    reporting_head = _git_head(ROOT)
    if (
        _git_head(dp_repo) != FIXED_DP_HEAD
        or _tracked_changes(dp_repo)
        or _tracked_changes(ROOT)
    ):
        raise ValueError("Fresh B4 reporting repository authority drifted")
    expected = _literal_expected_closeout(
        release=release,
        controller_path=controller_path,
        controller_root=controller_decision_root_sha256,
        release_path=release_path,
        release_root=opening_release_root_sha256,
        execution_path=execution_path,
        execution_root=execution_root_sha256,
        execution_review_path=execution_review_path,
        execution_review_root=execution_review_root_sha256,
        evaluation_path=evaluation_path,
        control=evidence,
        evaluation_review_path=evaluation_review_path,
        scientific_path=scientific_path,
        scientific=scientific,
        reporting_head=reporting_head,
    )
    closeout = _strict_canonical_json(source / "closeout.json")
    validate_closeout_literal(closeout, expected)
    report = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "status": REVIEW_STATUS,
        "reviewed_root_sha256": source_root_sha256,
        "holdout_identity_sha256": closeout["holdout_identity_sha256"],
        "experiment_protocol_sha256": closeout[
            "experiment_protocol_sha256"
        ],
        "execution_plan_sha256": closeout["execution_plan_sha256"],
        "run_nonce": closeout["run_nonce"],
        "opening_release_root_sha256": opening_release_root_sha256,
        "execution_root_sha256": execution_root_sha256,
        "execution_review_root_sha256": execution_review_root_sha256,
        "implementation_source_head": release["implementation_source_head"],
        "pointer_head_at_release": release["pointer_head_at_release"],
        "fixed_dp_head": FIXED_DP_HEAD,
        "reporting_machinery_head": reporting_head,
        "control_evidence_rehashed": True,
        "accepted_seals_independently_verified": True,
        "evaluation_artifact_created": False,
        "evaluation_root_sha256": None,
        "evaluation_review_started": False,
        "evaluation_review_artifact_created": False,
        "related_process_count": 0,
        "scientific_state_before": "full_denominator_formed",
        "planned_pair_count": 500,
        "complete_paired_row_count": 500,
        "planned_arm_run_count": 1500,
        "complete_arm_run_count": 1500,
        "terminal_arm_run_count": 1500,
        "full_denominator_formed": True,
        "raw_outcome_values_inspected": False,
        "rerun_allowed": False,
        "claim_authorized": False,
        "evaluation_result_status": UNAVAILABLE,
        "independent_oracle": "reviewer_local_literal_v1",
        "next_authority": NEXT_AUTHORITY,
    }
    return _write_atomic_review(output, report)


def validate_closeout_literal(
    value: dict[str, Any], expected: dict[str, Any]
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise ValueError("Fresh B4 literal closeout field set drifted")
    control = value.get("evaluation_control")
    if type(control) is not dict or set(control) != _CONTROL_FIELDS:
        raise ValueError("Fresh B4 literal control field set drifted")
    for name in ("command", "command_receipt", "run_exit_file", "stderr"):
        binding = control.get(name)
        if type(binding) is not dict or set(binding) != {"path", "sha256"}:
            raise ValueError("Fresh B4 literal file binding drifted")
    for name in (
        "controller_decision",
        "opening_release",
        "execution",
        "execution_review",
    ):
        binding = value.get(name)
        if type(binding) is not dict or set(binding) != {
            "path",
            "root_sha256",
        }:
            raise ValueError("Fresh B4 literal artifact binding drifted")
    ledger = value.get("scientific_ledger_before")
    if type(ledger) is not dict or set(ledger) != {"path", "sha256", "state"}:
        raise ValueError("Fresh B4 literal ledger binding drifted")
    unsigned = dict(value)
    payload_sha = unsigned.pop("closeout_payload_sha256", None)
    if payload_sha != canonical_sha256(unsigned):
        raise ValueError("Fresh B4 literal closeout payload SHA drifted")
    if not strict_equal(value, expected):
        raise ValueError("Fresh B4 literal closeout exact value drifted")
    return value


def _literal_expected_closeout(
    *,
    release: dict[str, Any],
    controller_path: Path,
    controller_root: str,
    release_path: Path,
    release_root: str,
    execution_path: Path,
    execution_root: str,
    execution_review_path: Path,
    execution_review_root: str,
    evaluation_path: Path,
    control: dict[str, Any],
    evaluation_review_path: Path,
    scientific_path: Path,
    scientific: dict[str, Any],
    reporting_head: str,
) -> dict[str, Any]:
    identity = release["holdout_identity"]["holdout_identity_sha256"]
    protocol = release["experiment_protocol"]["experiment_protocol_sha256"]
    if (
        scientific["state"] != "full_denominator_formed"
        or scientific["holdout_identity_sha256"] != identity
        or scientific["experiment_protocol_sha256"] != protocol
        or scientific["opening_release_root_sha256"] != release_root
        or scientific["run_nonce"] != release["run_nonce"]
        or scientific["planned_arm_run_count"] != 1500
        or scientific["terminal_arm_run_count"] != 1500
        or scientific["terminal_artifact_root_sha256"] is not None
    ):
        raise ValueError("Fresh B4 independent scientific ledger drifted")
    expected: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "benchmark": "fresh_b4",
        "phase": "evaluation",
        "block_class": "holdout_evaluation_control_fatal",
        "error_type": "ValueError",
        "error_message": ERROR_MESSAGE,
        "holdout_identity_sha256": identity,
        "experiment_protocol_sha256": protocol,
        "execution_plan_sha256": release["holdout_identity"][
            "execution_plan_sha256"
        ],
        "run_nonce": release["run_nonce"],
        "controller_decision": _binding(controller_path, controller_root),
        "opening_release": _binding(release_path, release_root),
        "execution": _binding(execution_path, execution_root),
        "execution_review": _binding(
            execution_review_path, execution_review_root
        ),
        "evaluation_output_dir": str(evaluation_path),
        "evaluation_control": control,
        "evaluation_artifact_created": False,
        "evaluation_root_sha256": None,
        "evaluation_review_output_dir": str(evaluation_review_path),
        "evaluation_review_started": False,
        "evaluation_review_artifact_created": False,
        "related_process_count": 0,
        "implementation_source_head": release["implementation_source_head"],
        "pointer_head_at_release": release["pointer_head_at_release"],
        "fixed_dp_head": FIXED_DP_HEAD,
        "reporting_machinery_head": reporting_head,
        "scientific_ledger_before": {
            "path": str(scientific_path),
            "sha256": _file_sha256(scientific_path),
            "state": "full_denominator_formed",
        },
        "planned_pair_count": 500,
        "complete_paired_row_count": 500,
        "planned_arm_run_count": 1500,
        "complete_arm_run_count": 1500,
        "terminal_arm_run_count": 1500,
        "full_denominator_formed": True,
        "outcome_fields_consumed": [],
        "raw_outcome_values_inspected": False,
        "rerun_allowed": False,
        "new_nonce_allowed": False,
        "alternate_directory_allowed": False,
        "suffix_allowed": False,
        "claim_authorized": False,
        "evaluation_result_status": UNAVAILABLE,
        "next_authority": NEXT_AUTHORITY,
    }
    expected["closeout_payload_sha256"] = canonical_sha256(expected)
    return expected


def _control_evidence(
    control: Path,
    *,
    release_path: Path,
    release_root: str,
    execution_path: Path,
    execution_root: str,
    execution_review_path: Path,
    execution_review_root: str,
    evaluation_path: Path,
) -> dict[str, Any]:
    if not control.is_dir() or control.is_symlink():
        raise ValueError("Fresh B4 evaluation control directory drifted")
    command = control / "run.sh"
    receipt = control / "run.sha256"
    run_exit = control / "run.exit"
    stderr = control / "stderr.log"
    for path in (command, receipt, run_exit, stderr):
        if not path.is_file() or path.is_symlink():
            raise ValueError("Fresh B4 evaluation control evidence drifted")
    command_sha = _file_sha256(command)
    if receipt.read_bytes() != f"{command_sha}  {command}\n".encode("utf-8"):
        raise ValueError("Fresh B4 evaluation command receipt drifted")
    if run_exit.read_bytes() != b"1\n":
        raise ValueError("Fresh B4 evaluation control run.exit drifted")
    command_text = command.read_text(encoding="utf-8")
    for fragment in (
        "scripts/integrations/evaluate_diffusion_planner_v25_holdout.py",
        str(release_path),
        release_root,
        str(execution_path),
        execution_root,
        str(execution_review_path),
        execution_review_root,
        str(evaluation_path),
    ):
        if fragment not in command_text:
            raise ValueError("Fresh B4 evaluation command binding drifted")
    stderr_text = stderr.read_text(encoding="utf-8")
    if (
        f'ValueError: {ERROR_MESSAGE}' not in stderr_text
        or f'raise ValueError("{ERROR_MESSAGE}")' not in stderr_text
    ):
        raise ValueError("Fresh B4 evaluation error signature drifted")
    return {
        "directory": str(control),
        "command": _file_binding(command),
        "command_receipt": _file_binding(receipt),
        "run_exit_file": _file_binding(run_exit),
        "run_exit": 1,
        "stderr": _file_binding(stderr),
    }


def _related_evaluation_processes(
    evaluation_path: Path, evaluation_review_path: Path
) -> list[int]:
    proc = Path("/proc")
    if not proc.is_dir():
        return []
    result: list[int] = []
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            tokens = [
                token.decode("utf-8", errors="replace")
                for token in (entry / "cmdline").read_bytes().split(b"\0")
                if token
            ]
        except OSError:
            continue
        if _command_targets(
            tokens,
            "evaluate_diffusion_planner_v25_holdout.py",
            evaluation_path,
        ) or _command_targets(
            tokens,
            "review_diffusion_planner_v25_holdout_evaluation.py",
            evaluation_review_path,
        ):
            result.append(int(entry.name))
    return sorted(result)


def _command_targets(tokens: list[str], script: str, output: Path) -> bool:
    return any(Path(token).name == script for token in tokens) and any(
        token == "--output-dir"
        and index + 1 < len(tokens)
        and Path(tokens[index + 1]).resolve() == output
        for index, token in enumerate(tokens)
    )


def _write_atomic_review(output: Path, report: dict[str, Any]) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent)
    )
    try:
        (staging / "report.json").write_bytes(canonical_json_bytes(report))
        (staging / "HEADS").write_bytes(
            (
                f"reporting_machinery_head={report['reporting_machinery_head']}\n"
                f"implementation_source_head={report['implementation_source_head']}\n"
                f"pointer_head_at_release={report['pointer_head_at_release']}\n"
                f"fixed_dp_head={FIXED_DP_HEAD}\n"
            ).encode("ascii")
        )
        (staging / "COMMAND").write_bytes(
            (" ".join(sys.argv) + "\n").encode("utf-8")
        )
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(
            staging, label="independent Fresh B4 evaluation terminal review"
        )
        os.rename(staging, output)
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _verify_root_receipt(root: Path, expected: str, *, label: str) -> None:
    manifest = root / "SHA256SUMS"
    receipt = root / "ROOT_SHA256SUMS"
    if (
        not root.is_dir()
        or root.is_symlink()
        or not manifest.is_file()
        or manifest.is_symlink()
        or not receipt.is_file()
        or receipt.is_symlink()
        or _file_sha256(manifest) != expected
        or receipt.read_bytes() != f"{expected}  SHA256SUMS\n".encode("ascii")
    ):
        raise ValueError(f"{label} seal receipt drifted")


def _binding(path: Path, root: str) -> dict[str, str]:
    return {"path": str(path), "root_sha256": root}


def _file_binding(path: Path) -> dict[str, str]:
    return {"path": str(path), "sha256": _file_sha256(path)}


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()


def _tracked_changes(repo: Path) -> bool:
    return bool(
        subprocess.check_output(
            [
                "git",
                "-C",
                str(repo),
                "status",
                "--porcelain",
                "--untracked-files=no",
            ],
            text=True,
        ).strip()
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-artifact", type=Path, required=True)
    parser.add_argument("--source-root-sha256", required=True)
    for name in (
        "controller-decision",
        "opening-release",
        "execution",
        "execution-review",
    ):
        parser.add_argument(f"--{name}-artifact", type=Path, required=True)
        parser.add_argument(f"--{name}-root-sha256", required=True)
    parser.add_argument("--evaluation-output-dir", type=Path, required=True)
    parser.add_argument("--evaluation-control-dir", type=Path, required=True)
    parser.add_argument(
        "--evaluation-review-output-dir", type=Path, required=True
    )
    parser.add_argument("--scientific-ledger-path", type=Path, required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    root = review(**vars(_arguments()))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
