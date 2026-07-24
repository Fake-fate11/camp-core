#!/usr/bin/env python3
"""Create a sealed generic holdout controller decision and opening release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (  # noqa: E402
    tracked_implementation_manifest,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (  # noqa: E402
    strict_equal,
)
from camp_core.integrations.diffusion_planner_v25_holdout_failure_closeout import (  # noqa: E402
    validate_consumed_holdout_failure_closeout,
)
from camp_core.integrations.diffusion_planner_v25_holdout_opening import (  # noqa: E402
    FIXED_DP_HEAD,
)
from camp_core.integrations.diffusion_planner_v25_holdout_opening_rc import (  # noqa: E402
    freeze_production_rc_controller_decision,
    freeze_production_rc_opening_release,
    validate_production_rc_controller_decision,
    validate_production_rc_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_holdout_state import (  # noqa: E402
    fail_operational_pre_exposure,
    operational_attempt_path,
    operational_identity_path,
    reserve_operational_attempt,
    scientific_identity_path,
    seal_operational_release,
)
from camp_core.integrations.diffusion_planner_v25_holdout_preopen_dispatch import (  # noqa: E402
    expected_holdout_preopen_review_status,
    validate_holdout_production_certificate,
    validate_holdout_preopen_authority,
)
from camp_core.integrations.diffusion_planner_v25_holdout_plan_dispatch import (  # noqa: E402
    NONFRESH_CANARY_SPLIT,
)
from camp_core.integrations.diffusion_planner_v25_upstream_authority_roles import (  # noqa: E402
    verify_upstream_authority_role_contract,
)
from camp_core.integrations.diffusion_planner_v25_production_equivalence_certificate import (  # noqa: E402
    validate_self_bound_production_equivalence_certificate,
)
from scripts.integrations.run_diffusion_planner_v25_fresh_b2_execution import (  # noqa: E402
    _canonical_json,
    _git_head,
    _tracked_dirty,
)


POINTER_ONLY_PATHS = frozenset(
    {
        "camp_core/tests/test_diffusion_planner_v25_iteration_audit.py",
        "docs/diffusion_planner_current_status.md",
        "docs/diffusion_planner_v25_iteration_audit.md",
    }
)
ROLES = (
    "preopen",
    "preopen_review",
    "production_preflight",
    "production_preflight_review",
    "b2_tombstone",
    "b2_failure_review",
)


def build(
    *,
    implementation_source_head: str,
    pointer_head_at_release: str,
    artifacts: Mapping[str, Path],
    roots: Mapping[str, str],
    run_nonce: str,
    authorized_output_dir: str,
    controller_output_dir: Path,
    release_output_dir: Path,
    cas_root: Path,
) -> dict[str, str]:
    qualified = _qualify_inputs(
        implementation_source_head=implementation_source_head,
        pointer_head_at_release=pointer_head_at_release,
        artifacts=artifacts,
        roots=roots,
        run_nonce=run_nonce,
        authorized_output_dir=authorized_output_dir,
        controller_output_dir=controller_output_dir,
        release_output_dir=release_output_dir,
        cas_root=cas_root,
    )
    preopen = qualified["preopen"]
    manifest = qualified["manifest"]
    bindings = qualified["bindings"]
    controller = freeze_production_rc_controller_decision(
        implementation_source_head=implementation_source_head,
        pointer_head_at_release=pointer_head_at_release,
        critical_implementation_manifest_sha256=manifest["manifest_sha256"],
        preopen_authority=bindings["preopen"],
        preopen_review=bindings["preopen_review"],
        production_composition_preflight=bindings["production_preflight"],
        production_composition_preflight_review=bindings[
            "production_preflight_review"
        ],
        b2_tombstone=bindings["b2_tombstone"],
        b2_failure_review=bindings["b2_failure_review"],
        holdout_identity=preopen["holdout_identity"],
        experiment_protocol=preopen["experiment_protocol"],
        run_nonce=run_nonce,
        authorized_output_dir=authorized_output_dir,
        cas_root=cas_root,
    )
    validate_production_rc_controller_decision(controller)
    controller_output_dir.mkdir(parents=True)
    _write_json(controller_output_dir / "decision.json", controller)
    _write_controls(
        controller_output_dir,
        source=implementation_source_head,
        pointer=pointer_head_at_release,
    )
    controller_root = seal_artifact(
        controller_output_dir, label="V25 holdout controller decision"
    )
    operational_path = reserve_operational_attempt(
        cas_root,
        holdout_identity_sha256=preopen["holdout_identity"][
            "holdout_identity_sha256"
        ],
        experiment_protocol_sha256=preopen["experiment_protocol"][
            "experiment_protocol_sha256"
        ],
        run_nonce=run_nonce,
        authorized_output_dir=authorized_output_dir,
        controller_root_sha256=controller_root,
    )
    try:
        release = freeze_production_rc_opening_release(
            implementation_source_head=implementation_source_head,
            pointer_head_at_release=pointer_head_at_release,
            critical_implementation_manifest_sha256=manifest[
                "manifest_sha256"
            ],
            controller_decision_root_sha256=controller_root,
            preopen_authority=bindings["preopen"],
            preopen_review=bindings["preopen_review"],
            production_composition_preflight=bindings[
                "production_preflight"
            ],
            production_composition_preflight_review=bindings[
                "production_preflight_review"
            ],
            b2_tombstone=bindings["b2_tombstone"],
            b2_failure_review=bindings["b2_failure_review"],
            holdout_identity=preopen["holdout_identity"],
            experiment_protocol=preopen["experiment_protocol"],
            run_nonce=run_nonce,
            authorized_output_dir=authorized_output_dir,
            cas_root=cas_root,
        )
        validate_production_rc_opening_release(release)
        if Path(release["operational_attempt_path"]).resolve() != operational_path:
            raise ValueError("holdout operational attempt path drifted")
        if Path(release["scientific_ledger_path"]).exists():
            raise FileExistsError(
                "holdout scientific identity was consumed before release"
            )
        release_output_dir.mkdir(parents=True)
        _write_json(release_output_dir / "decision.json", release)
        _write_controls(
            release_output_dir,
            source=implementation_source_head,
            pointer=pointer_head_at_release,
        )
        release_root = seal_artifact(
            release_output_dir, label="V25 holdout one-time opening release"
        )
        seal_operational_release(
            operational_path,
            opening_release_root_sha256=release_root,
        )
    except BaseException:
        if operational_path.exists():
            try:
                fail_operational_pre_exposure(
                    operational_path,
                    expected_state="release_reserved",
                    terminal_reason="opening_release_creation_failed",
                )
            except BaseException:
                pass
        raise
    return {
        "controller_decision_root_sha256": controller_root,
        "opening_release_root_sha256": release_root,
        "operational_attempt_path": str(operational_path),
        "scientific_ledger_path": release["scientific_ledger_path"],
    }


def qualify(
    *,
    implementation_source_head: str,
    pointer_head_at_release: str,
    artifacts: Mapping[str, Path],
    roots: Mapping[str, str],
    run_nonce: str,
    authorized_output_dir: str,
    controller_output_dir: Path,
    release_output_dir: Path,
    cas_root: Path,
) -> dict[str, Any]:
    qualified = _qualify_inputs(
        implementation_source_head=implementation_source_head,
        pointer_head_at_release=pointer_head_at_release,
        artifacts=artifacts,
        roots=roots,
        run_nonce=run_nonce,
        authorized_output_dir=authorized_output_dir,
        controller_output_dir=controller_output_dir,
        release_output_dir=release_output_dir,
        cas_root=cas_root,
    )
    preopen = qualified["preopen"]
    return {
        "schema_version": (
            "camp_dp_v25_holdout_opening_creator_exact_entry_"
            "qualification_v1"
        ),
        "status": "passed_no_side_effect_exact_entry_qualification",
        "implementation_source_head": implementation_source_head,
        "pointer_head_at_release": pointer_head_at_release,
        "critical_implementation_manifest_sha256": qualified["manifest"][
            "manifest_sha256"
        ],
        "preopen_root_sha256": roots["preopen"],
        "preopen_review_root_sha256": roots["preopen_review"],
        "holdout_identity_sha256": preopen["holdout_identity"][
            "holdout_identity_sha256"
        ],
        "experiment_protocol_sha256": preopen["experiment_protocol"][
            "experiment_protocol_sha256"
        ],
        "upstream_authority_role_contract_sha256": preopen[
            "upstream_authority_role_contract"
        ]["contract_sha256"],
        "run_nonce": run_nonce,
        "authorized_output_dir": authorized_output_dir,
        "controller_output_dir": str(controller_output_dir.resolve()),
        "release_output_dir": str(release_output_dir.resolve()),
        "cas_root": str(cas_root.resolve()),
        "controller_created": False,
        "release_created": False,
        "operational_attempt_created": False,
        "operational_identity_created": False,
        "scientific_ledger_created": False,
        "fresh_opened": False,
        "outcome_fields_consumed": [],
    }


def _qualify_inputs(
    *,
    implementation_source_head: str,
    pointer_head_at_release: str,
    artifacts: Mapping[str, Path],
    roots: Mapping[str, str],
    run_nonce: str,
    authorized_output_dir: str,
    controller_output_dir: Path,
    release_output_dir: Path,
    cas_root: Path,
) -> dict[str, Any]:
    if set(artifacts) != set(ROLES) or set(roots) != set(ROLES):
        raise ValueError("holdout opening input role set drifted")
    if (
        type(run_nonce) is not str
        or len(run_nonce) != 64
        or any(char not in "0123456789abcdef" for char in run_nonce)
    ):
        raise ValueError("holdout run nonce is not canonical")
    output_path = Path(authorized_output_dir)
    if (
        not output_path.is_absolute()
        or str(output_path.resolve()) != authorized_output_dir
    ):
        raise ValueError("holdout authorized output path is not canonical")
    if (
        controller_output_dir.exists()
        or release_output_dir.exists()
        or output_path.exists()
    ):
        raise FileExistsError("holdout controller/release/output exists")
    if _tracked_dirty(ROOT) or _git_head(ROOT) != pointer_head_at_release:
        raise ValueError("holdout live CAMP pointer is dirty or drifted")
    _verify_pointer_only_delta(
        implementation_source_head=implementation_source_head,
        pointer_head_at_release=pointer_head_at_release,
    )
    canonical = {name: Path(artifacts[name]).resolve() for name in ROLES}
    for role in ROLES:
        verify_complete_seal(canonical[role], roots[role], label=role)
        if (canonical[role] / "run.exit").read_bytes() != b"0\n":
            raise ValueError(f"{role} did not exit successfully")

    preopen = validate_holdout_preopen_authority(
        _canonical_json(canonical["preopen"] / "preopen_authority.json")
    )
    split = preopen["holdout_identity"]["split"]
    if split == "fresh_b4":
        verify_upstream_authority_role_contract(
            preopen["upstream_authority_role_contract"],
            bindings=preopen["upstream_bindings"],
        )
    elif split == NONFRESH_CANARY_SPLIT:
        sealed_bindings = dict(preopen["upstream_bindings"])
        sealed_bindings.update(preopen["source_fixture_bindings"])
        for upstream_role, upstream_binding in sealed_bindings.items():
            upstream_path = Path(upstream_binding["path"]).resolve()
            verify_complete_seal(
                upstream_path,
                upstream_binding["root_sha256"],
                label=f"{split} preopen upstream {upstream_role}",
            )
            if (upstream_path / "run.exit").read_bytes() != b"0\n":
                raise ValueError(
                    f"{split} preopen upstream did not pass: {upstream_role}"
                )
    preopen_review = _canonical_json(
        canonical["preopen_review"] / "report.json"
    )
    preflight_raw = _canonical_json(
        canonical["production_preflight"] / "preflight.json"
    )
    preflight_review = _canonical_json(
        canonical["production_preflight_review"] / "report.json"
    )
    b2_closeout = validate_consumed_holdout_failure_closeout(
        _canonical_json(canonical["b2_tombstone"] / "closeout.json")
    )
    b2_review = _canonical_json(
        canonical["b2_failure_review"] / "report.json"
    )
    manifest = tracked_implementation_manifest(ROOT)
    if split == "fresh_b4":
        preflight = validate_self_bound_production_equivalence_certificate(
            preflight_raw
        )
        preflight_binding_ok = (
            preopen.get("production_equivalence_certificate") == preflight
        )
    else:
        preflight = validate_holdout_production_certificate(
            preflight_raw,
            implementation_head=implementation_source_head,
            manifest_sha256=manifest["manifest_sha256"],
        )
    if split == NONFRESH_CANARY_SPLIT:
        preflight_binding_ok = (
            preflight.get("status")
            == "passed_exact_production_composition_preflight"
            and preflight.get("fresh_opened") is False
            and preflight.get("outcome_fields_consumed") == []
        )
    elif split != "fresh_b4":
        preflight_binding_ok = (
            preflight["holdout_identity"]["holdout_identity_sha256"]
            == preopen["holdout_identity"]["holdout_identity_sha256"]
            and preflight["experiment_protocol"][
                "experiment_protocol_sha256"
            ]
            == preopen["experiment_protocol"]["experiment_protocol_sha256"]
        )
    if (
        preopen["implementation_head"] != implementation_source_head
        or not strict_equal(preopen["critical_implementation_manifest"], manifest)
        or preopen_review.get("status")
        != expected_holdout_preopen_review_status(split)
        or preopen_review.get("reviewed_root_sha256") != roots["preopen"]
        or not preflight_binding_ok
        or preflight_review.get("status")
        not in {
            "passed_independent_production_composition_preflight_review",
            "passed_independent_fresh_b3_production_preflight_review",
            "passed_independent_nonfresh_production_equivalence_review",
        }
        or preflight_review.get("reviewed_root_sha256")
        not in {None, roots["production_preflight"]}
        or b2_review.get("status")
        != "passed_independent_consumed_holdout_failure_review"
        or b2_review.get("reviewed_root_sha256") != roots["b2_tombstone"]
        or b2_closeout["raw_outcome_values_inspected"] is not False
    ):
        raise ValueError("holdout sealed authority chain drifted")

    identity_sha = preopen["holdout_identity"]["holdout_identity_sha256"]
    state_paths = {
        "operational_attempt": operational_attempt_path(cas_root, run_nonce),
        "operational_identity": operational_identity_path(
            cas_root, identity_sha
        ),
        "scientific_ledger": scientific_identity_path(cas_root, identity_sha),
    }
    existing = [name for name, path in state_paths.items() if path.exists()]
    if existing:
        raise FileExistsError(
            "holdout one-time state already exists: " + ",".join(existing)
        )
    bindings = {
        name: {"path": str(canonical[name]), "root_sha256": roots[name]}
        for name in ROLES
    }
    return {
        "preopen": preopen,
        "manifest": manifest,
        "bindings": bindings,
    }


def _verify_pointer_only_delta(
    *, implementation_source_head: str, pointer_head_at_release: str
) -> None:
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", implementation_source_head, pointer_head_at_release],
        cwd=ROOT,
    ).returncode != 0:
        raise ValueError("holdout implementation is not a pointer ancestor")
    changed = set(
        subprocess.run(
            ["git", "diff", "--name-only", f"{implementation_source_head}..{pointer_head_at_release}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )
    if not changed.issubset(POINTER_ONLY_PATHS):
        raise ValueError("holdout source-to-pointer delta drifted")


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(
        (
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    )


def _write_controls(root: Path, *, source: str, pointer: str) -> None:
    (root / "HEADS").write_bytes(
        (
            f"camp_source_head={source}\n"
            f"camp_pointer_head={pointer}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (root / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (root / "run.exit").write_bytes(b"0\n")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation-source-head", required=True)
    parser.add_argument("--pointer-head-at-release", required=True)
    for role in ROLES:
        option = role.replace("_", "-")
        parser.add_argument(f"--{option}-artifact", type=Path, required=True)
        parser.add_argument(f"--{option}-root-sha256", required=True)
    parser.add_argument("--run-nonce", required=True)
    parser.add_argument("--authorized-output-dir", required=True)
    parser.add_argument("--controller-output-dir", type=Path, required=True)
    parser.add_argument("--release-output-dir", type=Path, required=True)
    parser.add_argument(
        "--cas-root",
        type=Path,
        default=Path("/root/autodl-tmp/.camp_dp_v25_holdout_identity_cas"),
    )
    parser.add_argument("--qualification-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    operation = qualify if args.qualification_only else build
    result = operation(
        implementation_source_head=args.implementation_source_head,
        pointer_head_at_release=args.pointer_head_at_release,
        artifacts={role: getattr(args, f"{role}_artifact") for role in ROLES},
        roots={role: getattr(args, f"{role}_root_sha256") for role in ROLES},
        run_nonce=args.run_nonce,
        authorized_output_dir=args.authorized_output_dir,
        controller_output_dir=args.controller_output_dir,
        release_output_dir=args.release_output_dir,
        cas_root=args.cas_root,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
