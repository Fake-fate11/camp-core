#!/usr/bin/env python3
"""Create the sealed controller decision and one-time Fresh B2 release."""

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
from camp_core.integrations.diffusion_planner_v25_calibration_artifact import (  # noqa: E402
    validate_calibration_freeze_payload,
)
from camp_core.integrations.diffusion_planner_v25_fresh_opening import (  # noqa: E402
    FIXED_DP_HEAD,
    FRESH_B2_CONTROLLER_ROLES,
    freeze_fresh_b2_controller_decision,
    freeze_fresh_b2_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_fresh_preopen_authority import (  # noqa: E402
    tracked_implementation_manifest,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    load_v25_runtime_selector_assets,
)
from scripts.integrations.run_diffusion_planner_v25_fresh_b2_execution import (  # noqa: E402
    _canonical_json,
    _file_sha256,
    _git_head,
    _legacy_json_object,
    _tracked_dirty,
    _verify_inputs,
)


POINTER_ONLY_PATHS = frozenset(
    {
        "camp_core/tests/test_diffusion_planner_v25_iteration_audit.py",
        "docs/diffusion_planner_current_status.md",
        "docs/diffusion_planner_v25_iteration_audit.md",
    }
)


def build(
    *,
    implementation_source_head: str,
    pointer_head_at_release: str,
    artifacts: Mapping[str, Path],
    roots: Mapping[str, str],
    probe_template: Path,
    probe_template_sha256: str,
    dp_repo: Path,
    run_nonce: str,
    authorized_output_dir: str,
    controller_output_dir: Path,
    release_output_dir: Path,
) -> dict[str, str]:
    if controller_output_dir.exists() or release_output_dir.exists():
        raise FileExistsError("Fresh B2 controller/release output already exists")
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree must be clean")
    if _git_head(ROOT) != pointer_head_at_release:
        raise ValueError("Fresh B2 live pointer HEAD drifted")
    dp_root = Path(dp_repo).resolve()
    if _git_head(dp_root) != FIXED_DP_HEAD or _tracked_dirty(dp_root):
        raise ValueError("fixed DP HEAD drifted or tracked worktree is dirty")
    _verify_pointer_only_delta(
        implementation_source_head=implementation_source_head,
        pointer_head_at_release=pointer_head_at_release,
    )
    canonical_artifacts = {
        role: Path(artifacts[role]).resolve() for role in FRESH_B2_CONTROLLER_ROLES
    }
    verified_roots = _verify_inputs(canonical_artifacts, roots)
    _legacy_json_object(Path(probe_template).resolve(), probe_template_sha256)

    preopen = _canonical_json(
        canonical_artifacts["preopen"] / "preopen_authority.json"
    )
    if preopen.get("implementation_head") != implementation_source_head:
        raise ValueError("Fresh B2 preopen implementation HEAD drifted")
    manifest = tracked_implementation_manifest(ROOT)
    if preopen.get("critical_implementation_manifest") != manifest:
        raise ValueError("Fresh B2 critical implementation manifest drifted")

    freeze_binding = preopen.get("upstream_bindings", {}).get(
        "calibration_freeze"
    )
    if (
        type(freeze_binding) is not dict
        or set(freeze_binding) != {"path", "root_sha256"}
    ):
        raise ValueError("Fresh B2 calibration freeze binding drifted")
    freeze_artifact = Path(freeze_binding["path"]).resolve()
    verify_complete_seal(
        freeze_artifact,
        freeze_binding["root_sha256"],
        label="Fresh B2 calibration freeze",
    )
    if (freeze_artifact / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh B2 calibration freeze did not exit successfully")
    freeze_payload = validate_calibration_freeze_payload(
        _canonical_json(freeze_artifact / "calibration_freeze.json")
    )
    calibration = freeze_payload["calibration_contract"]
    if (
        calibration["status"] != "calibration_freeze_passed"
        or calibration["fresh_preopen_qualification_allowed"] is not True
        or calibration["repeatability_estimation_status"]
        != "not_estimable_no_exact_candidate0_duplicates"
        or calibration["repeatability_gate_blocks_fresh"] is not False
    ):
        raise ValueError("Fresh B2 calibration freeze remains ineligible")

    assets = load_v25_runtime_selector_assets(
        training_artifact=canonical_artifacts["training"],
        training_root_sha256=verified_roots["training"],
        training_review_artifact=canonical_artifacts["training_review"],
        training_review_root_sha256=verified_roots["training_review"],
    )
    model_registry_sha256 = _file_sha256(
        canonical_artifacts["training"] / "model_registry.json"
    )
    input_bindings = {
        role: {
            "path": str(canonical_artifacts[role]),
            "root_sha256": verified_roots[role],
        }
        for role in FRESH_B2_CONTROLLER_ROLES
    }
    controller = freeze_fresh_b2_controller_decision(
        implementation_source_head=implementation_source_head,
        pointer_head_at_release=pointer_head_at_release,
        critical_implementation_manifest_sha256=manifest["manifest_sha256"],
        input_artifacts=input_bindings,
        probe_template_path=str(Path(probe_template).resolve()),
        probe_template_sha256=probe_template_sha256,
        dp_repo_path=str(dp_root),
        calibration_contract_root_sha256=freeze_binding["root_sha256"],
        preopen_qualification_root_sha256=verified_roots["preopen"],
        model_registry_sha256=model_registry_sha256,
        training_scale_sha256=assets.atom_scales_sha256,
        context_scaler_sha256=(
            assets.scene14d_weight_provider.context_scaler_sha256
        ),
        scenario_manifest_root_sha256=verified_roots["scenario_manifest"],
        run_nonce=run_nonce,
        authorized_output_dir=authorized_output_dir,
    )
    controller_output_dir.mkdir(parents=True)
    _write_json(controller_output_dir / "decision.json", controller)
    _write_controls(
        controller_output_dir,
        implementation_source_head=implementation_source_head,
        pointer_head=pointer_head_at_release,
    )
    controller_root = seal_artifact(
        controller_output_dir, label="V25 Fresh B2 controller decision"
    )

    release = freeze_fresh_b2_opening_release(
        implementation_source_head=implementation_source_head,
        pointer_head_at_release=pointer_head_at_release,
        controller_decision_root_sha256=controller_root,
        calibration_contract_root_sha256=controller[
            "calibration_contract_root_sha256"
        ],
        preopen_qualification_root_sha256=verified_roots["preopen"],
        model_registry_sha256=controller["model_registry_sha256"],
        training_scale_sha256=controller["training_scale_sha256"],
        context_scaler_sha256=controller["context_scaler_sha256"],
        scenario_manifest_root_sha256=verified_roots["scenario_manifest"],
        run_nonce=run_nonce,
        authorized_output_dir=authorized_output_dir,
    )
    release_output_dir.mkdir(parents=True)
    _write_json(release_output_dir / "decision.json", release)
    _write_controls(
        release_output_dir,
        implementation_source_head=implementation_source_head,
        pointer_head=pointer_head_at_release,
    )
    release_root = seal_artifact(
        release_output_dir, label="V25 Fresh B2 one-time opening release"
    )
    return {
        "controller_decision_root_sha256": controller_root,
        "opening_release_root_sha256": release_root,
    }


def _verify_pointer_only_delta(
    *, implementation_source_head: str, pointer_head_at_release: str
) -> None:
    if (
        subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                implementation_source_head,
                pointer_head_at_release,
            ],
            cwd=ROOT,
        ).returncode
        != 0
    ):
        raise ValueError("Fresh B2 implementation is not an ancestor of pointer")
    changed = set(
        subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                f"{implementation_source_head}..{pointer_head_at_release}",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )
    if changed != POINTER_ONLY_PATHS:
        raise ValueError("Fresh B2 source-to-pointer delta drifted")


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


def _write_controls(
    root: Path, *, implementation_source_head: str, pointer_head: str
) -> None:
    (root / "HEADS").write_bytes(
        (
            f"camp_source_head={implementation_source_head}\n"
            f"camp_pointer_head={pointer_head}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (root / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (root / "run.exit").write_bytes(b"0\n")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation-source-head", required=True)
    parser.add_argument("--pointer-head-at-release", required=True)
    for role in FRESH_B2_CONTROLLER_ROLES:
        option = role.replace("_", "-")
        parser.add_argument(f"--{option}-artifact", type=Path, required=True)
        parser.add_argument(f"--{option}-root-sha256", required=True)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--probe-template-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--run-nonce", required=True)
    parser.add_argument("--authorized-output-dir", required=True)
    parser.add_argument("--controller-output-dir", type=Path, required=True)
    parser.add_argument("--release-output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    artifacts = {
        role: getattr(args, f"{role}_artifact")
        for role in FRESH_B2_CONTROLLER_ROLES
    }
    roots = {
        role: getattr(args, f"{role}_root_sha256")
        for role in FRESH_B2_CONTROLLER_ROLES
    }
    result = build(
        implementation_source_head=args.implementation_source_head,
        pointer_head_at_release=args.pointer_head_at_release,
        artifacts=artifacts,
        roots=roots,
        probe_template=args.probe_template,
        probe_template_sha256=args.probe_template_sha256,
        dp_repo=args.dp_repo,
        run_nonce=args.run_nonce,
        authorized_output_dir=args.authorized_output_dir,
        controller_output_dir=args.controller_output_dir,
        release_output_dir=args.release_output_dir,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
