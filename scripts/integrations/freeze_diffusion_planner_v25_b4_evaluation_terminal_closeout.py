#!/usr/bin/env python3
"""Seal the outcome-blind Fresh B4 post-exposure evaluation failure."""

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
from camp_core.integrations.diffusion_planner_v25_b4_evaluation_terminal_closeout import (  # noqa: E402,E501
    ERROR_MESSAGE,
    FIXED_DP_HEAD,
    freeze_b4_evaluation_terminal_closeout,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (  # noqa: E402,E501
    _strict_canonical_json,
    canonical_json_bytes,
)
from camp_core.integrations.diffusion_planner_v25_holdout_opening import (  # noqa: E402
    validate_holdout_controller_decision,
    validate_holdout_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_holdout_state import (  # noqa: E402
    validate_scientific_ledger,
)


def build(
    *,
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
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
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

    controller = validate_holdout_controller_decision(
        _strict_canonical_json(controller_path / "decision.json")
    )
    release = validate_holdout_opening_release(
        _strict_canonical_json(release_path / "decision.json")
    )
    review_report = _strict_canonical_json(
        execution_review_path / "report.json"
    )
    independent = review_report.get("independent_execution_review")
    if (
        controller["holdout_identity"] != release["holdout_identity"]
        or controller["experiment_protocol"] != release["experiment_protocol"]
        or release["controller_decision_root_sha256"]
        != controller_decision_root_sha256
        or release["fixed_dp_head"] != FIXED_DP_HEAD
        or review_report.get("status")
        != "passed_independent_holdout_execution_review"
        or review_report.get("reviewed_root_sha256") != execution_root_sha256
        or review_report.get("opening_release_root_sha256")
        != opening_release_root_sha256
        or review_report.get("holdout_identity_sha256")
        != release["holdout_identity"]["holdout_identity_sha256"]
        or review_report.get("experiment_protocol_sha256")
        != release["experiment_protocol"]["experiment_protocol_sha256"]
        or review_report.get("full_denominator_formed") is not True
        or type(independent) is not dict
        or independent.get("planned_pair_count") != 500
        or independent.get("reviewed_arm_run_count") != 1500
        or independent.get("complete_arm_run_count") != 1500
    ):
        raise ValueError("Fresh B4 accepted authority chain drifted")

    if evaluation_path.exists():
        raise ValueError("Fresh B4 evaluation artifact unexpectedly exists")
    if evaluation_review_path.exists():
        raise ValueError("Fresh B4 evaluation review unexpectedly exists")
    related = _related_evaluation_processes(
        evaluation_path, evaluation_review_path
    )
    if related:
        raise ValueError("Fresh B4 evaluation process still exists")
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

    scientific = validate_scientific_ledger(
        _strict_canonical_json(scientific_path)
    )
    identity = release["holdout_identity"]["holdout_identity_sha256"]
    protocol = release["experiment_protocol"]["experiment_protocol_sha256"]
    if (
        scientific["state"] != "full_denominator_formed"
        or scientific["holdout_identity_sha256"] != identity
        or scientific["experiment_protocol_sha256"] != protocol
        or scientific["opening_release_root_sha256"]
        != opening_release_root_sha256
        or scientific["run_nonce"] != release["run_nonce"]
        or scientific["planned_arm_run_count"] != 1500
        or scientific["terminal_arm_run_count"] != 1500
        or scientific["terminal_artifact_root_sha256"] is not None
    ):
        raise ValueError("Fresh B4 scientific ledger drifted")
    if (
        _git_head(dp_repo) != FIXED_DP_HEAD
        or _tracked_changes(dp_repo)
        or _tracked_changes(ROOT)
    ):
        raise ValueError("Fresh B4 reporting repository authority drifted")

    closeout = freeze_b4_evaluation_terminal_closeout(
        holdout_identity_sha256=identity,
        experiment_protocol_sha256=protocol,
        execution_plan_sha256=release["holdout_identity"][
            "execution_plan_sha256"
        ],
        run_nonce=release["run_nonce"],
        controller_decision=_binding(
            controller_path, controller_decision_root_sha256
        ),
        opening_release=_binding(release_path, opening_release_root_sha256),
        execution=_binding(execution_path, execution_root_sha256),
        execution_review=_binding(
            execution_review_path, execution_review_root_sha256
        ),
        evaluation_output_dir=str(evaluation_path),
        evaluation_control=evidence,
        evaluation_review_output_dir=str(evaluation_review_path),
        implementation_source_head=release["implementation_source_head"],
        pointer_head_at_release=release["pointer_head_at_release"],
        reporting_machinery_head=_git_head(ROOT),
        scientific_ledger_before={
            "path": str(scientific_path),
            "sha256": _file_sha256(scientific_path),
            "state": scientific["state"],
        },
    )
    return _write_atomic_artifact(
        output,
        payload_name="closeout.json",
        payload=closeout,
        label="Fresh B4 evaluation terminal closeout",
    )


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
    command_receipt = control / "run.sha256"
    run_exit = control / "run.exit"
    stderr = control / "stderr.log"
    for path in (command, command_receipt, run_exit, stderr):
        if not path.is_file() or path.is_symlink():
            raise ValueError("Fresh B4 evaluation control evidence drifted")
    command_sha = _file_sha256(command)
    if command_receipt.read_bytes() != (
        f"{command_sha}  {command}\n".encode("utf-8")
    ):
        raise ValueError("Fresh B4 evaluation command receipt drifted")
    if run_exit.read_bytes() != b"1\n":
        raise ValueError("Fresh B4 evaluation control run.exit drifted")
    command_text = command.read_text(encoding="utf-8")
    expected_fragments = (
        "scripts/integrations/evaluate_diffusion_planner_v25_holdout.py",
        str(release_path),
        release_root,
        str(execution_path),
        execution_root,
        str(execution_review_path),
        execution_review_root,
        str(evaluation_path),
    )
    if any(fragment not in command_text for fragment in expected_fragments):
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
        "command_receipt": _file_binding(command_receipt),
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
    matches: list[int] = []
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        tokens = [
            token.decode("utf-8", errors="replace")
            for token in raw.split(b"\0")
            if token
        ]
        if _command_targets(
            tokens,
            "evaluate_diffusion_planner_v25_holdout.py",
            evaluation_path,
        ) or _command_targets(
            tokens,
            "review_diffusion_planner_v25_holdout_evaluation.py",
            evaluation_review_path,
        ):
            matches.append(int(entry.name))
    return sorted(matches)


def _command_targets(tokens: list[str], script: str, output: Path) -> bool:
    if not any(Path(token).name == script for token in tokens):
        return False
    return any(
        token == "--output-dir"
        and index + 1 < len(tokens)
        and Path(tokens[index + 1]).resolve() == output
        for index, token in enumerate(tokens)
    )


def _write_atomic_artifact(
    output: Path,
    *,
    payload_name: str,
    payload: dict[str, Any],
    label: str,
) -> str:
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent)
    )
    try:
        (staging / payload_name).write_bytes(canonical_json_bytes(payload))
        (staging / "HEADS").write_bytes(
            (
                f"reporting_machinery_head={_git_head(ROOT)}\n"
                f"implementation_source_head={payload['implementation_source_head']}\n"
                f"pointer_head_at_release={payload['pointer_head_at_release']}\n"
                f"fixed_dp_head={FIXED_DP_HEAD}\n"
            ).encode("ascii")
        )
        (staging / "COMMAND").write_bytes(
            (" ".join(sys.argv) + "\n").encode("utf-8")
        )
        (staging / "run.exit").write_bytes(b"0\n")
        root = seal_artifact(staging, label=label)
        os.rename(staging, output)
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _verify_root_receipt(root: Path, expected: str, *, label: str) -> None:
    if not root.is_dir() or root.is_symlink():
        raise ValueError(f"{label} root drifted")
    manifest = root / "SHA256SUMS"
    receipt = root / "ROOT_SHA256SUMS"
    if (
        not manifest.is_file()
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
    root = build(**vars(_arguments()))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
