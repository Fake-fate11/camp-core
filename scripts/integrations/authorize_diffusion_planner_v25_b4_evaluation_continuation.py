#!/usr/bin/env python3
"""Atomically authorize the single Fresh B4 corrected-evaluation continuation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_b4_evaluation_continuation import (  # noqa: E402,E501
    authorize_from_preserved_denominator,
)
from camp_core.integrations.diffusion_planner_v25_b4_evaluation_policy_correction import (  # noqa: E402,E501
    EXPERIMENT_PROTOCOL_SHA256,
    HOLDOUT_IDENTITY_SHA256,
    OLD_TERMINAL_HISTORY,
    OLD_TERMINAL_LEDGER_SHA256,
    OLD_TERMINAL_REASON,
    OPENING_RELEASE_ROOT_SHA256,
    RUN_NONCE,
    validate_correction_authority,
    validate_correction_authority_review,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (  # noqa: E402
    _strict_canonical_json,
)
from camp_core.integrations.diffusion_planner_v25_holdout_state import (  # noqa: E402
    validate_scientific_ledger,
)


def authorize(
    *,
    authority_artifact: Path,
    authority_root_sha256: str,
    authority_review_artifact: Path,
    authority_review_root_sha256: str,
    scientific_ledger_path: Path,
) -> Path:
    authority_path = Path(authority_artifact).resolve()
    review_path = Path(authority_review_artifact).resolve()
    for label, path, root in (
        ("correction authority", authority_path, authority_root_sha256),
        ("correction authority review", review_path, authority_review_root_sha256),
    ):
        verify_complete_seal(path, root, label=f"Fresh B4 {label}")
        if (path / "run.exit").read_bytes() != b"0\n":
            raise ValueError(f"Fresh B4 {label} did not pass")
    authority = validate_correction_authority(
        _object(authority_path / "authority.json")
    )
    review = validate_correction_authority_review(
        _object(review_path / "report.json")
    )
    if (
        review["reviewed_authority"]
        != {"path": str(authority_path), "root_sha256": authority_root_sha256}
        or authority["corrected_evaluation_output_dir"]
        != review["corrected_evaluation_output_dir"]
        or authority["corrected_evaluation_review_output_dir"]
        != review["corrected_evaluation_review_output_dir"]
        or authority["continuation"] != review["continuation"]
    ):
        raise ValueError("Fresh B4 correction authority review binding drifted")
    scientific_path = Path(scientific_ledger_path).resolve()
    scientific = validate_scientific_ledger(
        _strict_canonical_json(scientific_path)
    )
    if (
        _file_sha256(scientific_path) != OLD_TERMINAL_LEDGER_SHA256
        or scientific["state"] != "terminal_failure"
        or tuple(scientific["history"]) != OLD_TERMINAL_HISTORY
        or scientific["terminal_reason"] != OLD_TERMINAL_REASON
    ):
        raise ValueError("Fresh B4 preserved terminal ledger drifted")
    if (
        Path(authority["corrected_evaluation_output_dir"]).exists()
        or Path(authority["corrected_evaluation_review_output_dir"]).exists()
    ):
        raise FileExistsError("Fresh B4 corrected evaluation already exists")
    ledger_path, _ = authorize_from_preserved_denominator(
        cas_namespace=Path(authority["continuation"]["cas_namespace"]),
        identity_slot_namespace=Path(
            authority["continuation"]["identity_slot_namespace"]
        ),
        holdout_identity_sha256=HOLDOUT_IDENTITY_SHA256,
        experiment_protocol_sha256=EXPERIMENT_PROTOCOL_SHA256,
        run_nonce=RUN_NONCE,
        opening_release_root_sha256=OPENING_RELEASE_ROOT_SHA256,
        old_terminal_ledger_path=str(scientific_path),
        old_terminal_ledger_sha256=OLD_TERMINAL_LEDGER_SHA256,
        old_terminal_reason=OLD_TERMINAL_REASON,
        correction_authority_root_sha256=authority_root_sha256,
        correction_authority_review_root_sha256=authority_review_root_sha256,
        corrected_evaluation_output_dir=authority[
            "corrected_evaluation_output_dir"
        ],
        corrected_evaluation_review_output_dir=authority[
            "corrected_evaluation_review_output_dir"
        ],
    )
    return ledger_path


def _object(path: Path) -> dict[str, Any]:
    value = _strict_canonical_json(path)
    if type(value) is not dict:
        raise ValueError(f"Fresh B4 JSON object drifted: {path}")
    return value


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority-artifact", type=Path, required=True)
    parser.add_argument("--authority-root-sha256", required=True)
    parser.add_argument("--authority-review-artifact", type=Path, required=True)
    parser.add_argument("--authority-review-root-sha256", required=True)
    parser.add_argument("--scientific-ledger-path", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    path = authorize(**vars(_arguments()))
    print(json.dumps({"status": "passed", "continuation_ledger": str(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
