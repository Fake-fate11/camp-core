#!/usr/bin/env python3
"""Materialize the single outcome-blind Fresh B4 consolidated pre-open authority."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_b3_preopen import (
    validate_b3_preopen_authority,
)
from camp_core.integrations.diffusion_planner_v25_b4_preopen import (
    FIXED_DP_HEAD,
    build_b4_holdout_identity,
    build_b4_preopen_authority,
)
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (
    canonical_json_bytes,
    tracked_implementation_manifest,
)
from camp_core.integrations.diffusion_planner_v25_holdout_state import (
    operational_identity_path,
    scientific_identity_path,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (
    build_signal_complete_suite,
    validate_signal_complete_suite,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (
    build_signal_complete_runtime_case,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_routes import (
    materialize_signal_complete_route_assets,
    validate_signal_complete_route_assets,
)
from camp_core.integrations.diffusion_planner_v25_upstream_authority_roles import (
    freeze_upstream_authority_role_contract,
)
from scripts.integrations.freeze_diffusion_planner_v25_fresh_b2_preopen import (
    _canonical_json,
    _open_atom_mechanism,
    _open_calibration_freeze,
    _open_storage,
    _open_upstream,
    _validate_config,
)
from scripts.integrations.materialize_diffusion_planner_v25_signal_complete_routes import (
    _route_class,
)


SCHEMA_VERSION = "camp_dp_v25_fresh_b4_preopen_materialization_v2"
CAS_ROOT = Path("/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas")


def build(
    *,
    config_path: Path,
    accepted_b3_preopen_artifact: Path,
    accepted_b3_preopen_root_sha256: str,
    accepted_b3_preopen_review_artifact: Path,
    accepted_b3_preopen_review_root_sha256: str,
    storage_artifact: Path,
    storage_root_sha256: str,
    storage_review_artifact: Path,
    storage_review_root_sha256: str,
    atom_mechanism_artifact: Path,
    atom_mechanism_root_sha256: str,
    atom_mechanism_review_artifact: Path,
    atom_mechanism_review_root_sha256: str,
    calibration_freeze_artifact: Path,
    calibration_freeze_root_sha256: str,
    calibration_freeze_review_artifact: Path,
    calibration_freeze_review_root_sha256: str,
    b2_failure_closeout_artifact: Path,
    b2_failure_closeout_root_sha256: str,
    b2_failure_review_artifact: Path,
    b2_failure_review_root_sha256: str,
    b3_terminal_closeout_artifact: Path,
    b3_terminal_closeout_root_sha256: str,
    b3_terminal_closeout_review_artifact: Path,
    b3_terminal_closeout_review_root_sha256: str,
    production_certificate_artifact: Path,
    production_certificate_root_sha256: str,
    production_certificate_review_artifact: Path,
    production_certificate_review_root_sha256: str,
    output_dir: Path,
) -> str:
    if _tracked_dirty():
        raise ValueError("CAMP tracked worktree must be clean")
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    config = _validate_config(_canonical_json(config_path))
    upstream = _open_upstream(config)
    calibration = _open_calibration_freeze(
        artifact=calibration_freeze_artifact,
        root_sha256=calibration_freeze_root_sha256,
        review_artifact=calibration_freeze_review_artifact,
        review_root_sha256=calibration_freeze_review_root_sha256,
    )
    upstream["bindings"].update(calibration["bindings"])
    storage = _open_storage(
        storage_artifact=storage_artifact,
        storage_root_sha256=storage_root_sha256,
        storage_review_artifact=storage_review_artifact,
        storage_review_root_sha256=storage_review_root_sha256,
    )
    atom = _open_atom_mechanism(
        artifact=atom_mechanism_artifact,
        root_sha256=atom_mechanism_root_sha256,
        review_artifact=atom_mechanism_review_artifact,
        review_root_sha256=atom_mechanism_review_root_sha256,
    )
    prior = _open_b3_preopen(
        artifact=accepted_b3_preopen_artifact,
        root_sha256=accepted_b3_preopen_root_sha256,
        review_artifact=accepted_b3_preopen_review_artifact,
        review_root_sha256=accepted_b3_preopen_review_root_sha256,
    )
    b2_closeout = _open_payload(
        b2_failure_closeout_artifact,
        b2_failure_closeout_root_sha256,
        "closeout.json",
    )
    b2_review = _open_payload(
        b2_failure_review_artifact,
        b2_failure_review_root_sha256,
        "report.json",
    )
    b3_closeout = _open_payload(
        b3_terminal_closeout_artifact,
        b3_terminal_closeout_root_sha256,
        "closeout.json",
    )
    b3_review = _open_payload(
        b3_terminal_closeout_review_artifact,
        b3_terminal_closeout_review_root_sha256,
        "report.json",
    )
    certificate = _open_payload(
        production_certificate_artifact,
        production_certificate_root_sha256,
        "preflight.json",
    )
    certificate_review = _open_payload(
        production_certificate_review_artifact,
        production_certificate_review_root_sha256,
        "report.json",
    )
    suite_full = build_signal_complete_suite("fresh_b4")
    suite_receipt = validate_signal_complete_suite(suite_full)
    plan = build_signal_complete_execution_plan("fresh_b4")

    output.mkdir(parents=True)
    try:
        maps_root = output / "maps"
        maps_root.mkdir()
        for relative, payload in suite_full["map_payloads"].items():
            path = maps_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        route_class, _route_source = _route_class(
            Path("/root/autodl-tmp/Diffusion-Planner")
        )
        route_root = output / "route_materialization"
        route_manifest = materialize_signal_complete_route_assets(
            plan=plan,
            map_artifact=maps_root,
            output_dir=route_root,
            route_class=route_class,
        )
        route_manifest = validate_signal_complete_route_assets(
            route_manifest,
            plan=plan,
            map_artifact=maps_root,
            route_class=route_class,
        )
        _write(route_root / "route_assets.json", route_manifest)
        prepared = [
            build_signal_complete_runtime_case(
                identity,
                map_artifact=maps_root,
                seeds=plan["seeds"],
            )
            for identity in plan["identities"]
        ]
        bindings = dict(upstream["bindings"])
        bindings.update(
            {
                "accepted_b3_preopen": _binding(
                    accepted_b3_preopen_artifact,
                    accepted_b3_preopen_root_sha256,
                ),
                "accepted_b3_preopen_review": _binding(
                    accepted_b3_preopen_review_artifact,
                    accepted_b3_preopen_review_root_sha256,
                ),
                "storage": _binding(storage_artifact, storage_root_sha256),
                "storage_review": _binding(
                    storage_review_artifact, storage_review_root_sha256
                ),
                "atom_mechanism": _binding(
                    atom_mechanism_artifact, atom_mechanism_root_sha256
                ),
                "atom_mechanism_review": _binding(
                    atom_mechanism_review_artifact,
                    atom_mechanism_review_root_sha256,
                ),
                "b2_consumed_failure": _binding(
                    b2_failure_closeout_artifact,
                    b2_failure_closeout_root_sha256,
                ),
                "b2_consumed_failure_review": _binding(
                    b2_failure_review_artifact,
                    b2_failure_review_root_sha256,
                ),
                "b3_terminal_closeout": _binding(
                    b3_terminal_closeout_artifact,
                    b3_terminal_closeout_root_sha256,
                ),
                "b3_terminal_closeout_review": _binding(
                    b3_terminal_closeout_review_artifact,
                    b3_terminal_closeout_review_root_sha256,
                ),
                "production_equivalence_certificate": _binding(
                    production_certificate_artifact,
                    production_certificate_root_sha256,
                ),
                "production_equivalence_certificate_review": _binding(
                    production_certificate_review_artifact,
                    production_certificate_review_root_sha256,
                ),
            }
        )
        upstream_role_contract = freeze_upstream_authority_role_contract(
            bindings
        )
        identity = build_b4_holdout_identity(suite=suite_full, plan=plan)
        identity_sha = identity["holdout_identity_sha256"]
        operational_exists = operational_identity_path(
            CAS_ROOT, identity_sha
        ).exists()
        scientific_exists = scientific_identity_path(
            CAS_ROOT, identity_sha
        ).exists()
        authority = build_b4_preopen_authority(
            implementation_head=_git_head(),
            critical_implementation_manifest=tracked_implementation_manifest(
                ROOT
            ),
            upstream_bindings=bindings,
            upstream_authority_role_contract=upstream_role_contract,
            train_source_rows=upstream["train_source_rows"],
            calibration_plan=build_signal_complete_execution_plan(
                "calibration"
            ),
            b2_plan=build_signal_complete_execution_plan("fresh_b2"),
            b3_plan=build_signal_complete_execution_plan("fresh_b3"),
            b4_suite=suite_full,
            b4_plan=plan,
            b4_map_artifact=maps_root,
            route_asset_manifest=route_manifest,
            license_sha256=_sha256(ROOT / "LICENSE"),
            prepared_runtime_cases=prepared,
            prior_experiment_protocol=prior["experiment_protocol"],
            b2_consumed_failure=b2_closeout,
            b2_consumed_failure_review=b2_review,
            b3_terminal_closeout=b3_closeout,
            b3_terminal_closeout_review=b3_review,
            production_equivalence_certificate=certificate,
            production_equivalence_certificate_review=certificate_review,
            power=prior["power"],
            evaluation=prior["evaluation"],
            storage_manifest=storage["manifest"],
            atom_mechanism_binding=bindings["atom_mechanism"],
            atom_mechanism_review_binding=bindings[
                "atom_mechanism_review"
            ],
            free_bytes_before=shutil.disk_usage(output.parent).free,
            output_parent=output.parent,
            operational_attempt_exists=operational_exists,
            scientific_ledger_exists=scientific_exists,
        )
        _write(output / "fresh_b4_map_suite.json", suite_receipt)
        _write(output / "fresh_b4_execution_plan.json", plan)
        _write(output / "fresh_b4_route_assets.json", route_manifest)
        _write(output / "fresh_b4_prepared_runtime_cases.json", prepared)
        _write(output / "preopen_authority.json", authority)
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": "passed_outcome_blind_fresh_b4_preopen_materialization",
            "camp_head": _git_head(),
            "fixed_dp_head": FIXED_DP_HEAD,
            "preopen_authority_sha256": _sha256(
                output / "preopen_authority.json"
            ),
            "holdout_identity_sha256": identity_sha,
            "experiment_protocol_sha256": authority[
                "experiment_protocol"
            ]["experiment_protocol_sha256"],
            "production_equivalence_certificate_root_sha256": (
                production_certificate_root_sha256
            ),
            "paired_unit_count": 500,
            "arm_run_count": 1500,
            "tick_capacity": 96_000,
            "prior_holdout_raw_values_used": False,
            "fresh_open_authorized": False,
            "operational_attempt_exists": operational_exists,
            "scientific_ledger_exists": scientific_exists,
            "fresh_b4_opened": False,
            "outcome_fields_consumed": [],
        }
        _write(output / "report.json", report)
        (output / "HEADS").write_bytes(
            (
                f"camp_head={report['camp_head']}\n"
                f"fixed_dp_head={FIXED_DP_HEAD}\n"
            ).encode("ascii")
        )
        (output / "COMMAND").write_bytes(
            (" ".join(sys.argv) + "\n").encode("utf-8")
        )
        (output / "run.exit").write_bytes(b"0\n")
        return seal_artifact(
            output, label="V25 Fresh B4 consolidated pre-open authority"
        )
    except BaseException as exc:
        _write(
            output / "failure.json",
            {
                "schema_version": SCHEMA_VERSION,
                "status": "failed_fresh_b4_preopen_materialization",
                "reason": str(exc),
                "fresh_b4_opened": False,
                "outcome_fields_consumed": [],
            },
        )
        (output / "run.exit").write_bytes(b"1\n")
        seal_artifact(output, label="failed V25 Fresh B4 pre-open authority")
        raise


def _open_b3_preopen(
    *,
    artifact: Path,
    root_sha256: str,
    review_artifact: Path,
    review_root_sha256: str,
) -> dict[str, Any]:
    authority = validate_b3_preopen_authority(
        _open_payload(artifact, root_sha256, "preopen_authority.json")
    )
    review = _open_payload(
        review_artifact, review_root_sha256, "report.json"
    )
    if (
        review.get("status") != "passed_independent_fresh_b3_preopen_review"
        or review.get("reviewed_root_sha256") != root_sha256
    ):
        raise ValueError("accepted B3 preopen review binding drifted")
    return authority


def _open_payload(
    artifact: Path, root_sha256: str, relative: str
) -> dict[str, Any]:
    verify_complete_seal(artifact, root_sha256, label=relative)
    if (artifact / "run.exit").read_bytes() != b"0\n":
        raise ValueError(f"{relative} exit drifted")
    return _canonical_json(artifact / relative)


def _binding(path: Path, root_sha256: str) -> dict[str, str]:
    return {"path": str(path.resolve()), "root_sha256": root_sha256}


def _write(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes(value))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def _tracked_dirty() -> bool:
    return bool(
        subprocess.check_output(
            [
                "git",
                "-C",
                str(ROOT),
                "status",
                "--short",
                "--untracked-files=no",
            ],
            text=True,
        ).strip()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    for name in (
        "accepted-b3-preopen",
        "accepted-b3-preopen-review",
        "storage",
        "storage-review",
        "atom-mechanism",
        "atom-mechanism-review",
        "calibration-freeze",
        "calibration-freeze-review",
        "b2-failure-closeout",
        "b2-failure-review",
        "b3-terminal-closeout",
        "b3-terminal-closeout-review",
        "production-certificate",
        "production-certificate-review",
    ):
        parser.add_argument(f"--{name}-artifact", type=Path, required=True)
        parser.add_argument(f"--{name}-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    kwargs = vars(args)
    kwargs["config_path"] = kwargs.pop("config")
    root = build(**kwargs)
    print(root)


if __name__ == "__main__":
    main()
