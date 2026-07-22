#!/usr/bin/env python3
"""Independently review one sealed V25 Fresh B2 three-arm execution."""

from __future__ import annotations

import argparse
import hashlib
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
from camp_core.integrations.diffusion_planner_v25_fresh_execution_review import (  # noqa: E402
    review_fresh_b2_three_arm_execution,
)
from camp_core.integrations.diffusion_planner_v25_fresh_opening import (  # noqa: E402
    validate_fresh_b2_opening_consumption,
    validate_fresh_b2_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    load_v25_runtime_selector_assets,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (  # noqa: E402
    validate_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (  # noqa: E402
    build_signal_complete_runtime_case,
)
from scripts.integrations.run_diffusion_planner_v25_fresh_b2_execution import (  # noqa: E402
    FIXED_DP_HEAD,
    INPUT_ROLES,
    SCHEMA_VERSION as EXECUTION_ARTIFACT_SCHEMA_VERSION,
    _canonical_bytes,
    _canonical_json,
    _file_sha256,
    _git_head,
    _legacy_json_object,
    _route_assets,
    _runtime_selector_authority,
    _tracked_dirty,
    _verify_inputs,
    _write_json,
)


SCHEMA_VERSION = "camp_dp_v25_fresh_b2_execution_review_artifact_v1"


def review(
    *,
    artifact: Path,
    artifact_root_sha256: str,
    artifacts: Mapping[str, Path],
    roots: Mapping[str, str],
    probe_template: Path,
    probe_template_sha256: str,
    opening_release_artifact: Path,
    opening_release_root_sha256: str,
    dp_repo: Path,
    output_dir: Path,
) -> str:
    execution = Path(artifact).resolve()
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
    execution_seal = verify_complete_seal(
        execution, artifact_root_sha256, label="Fresh B2 execution"
    )
    if (execution / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh B2 execution did not exit successfully")
    dp_root = Path(dp_repo).resolve()
    if _git_head(dp_root) != FIXED_DP_HEAD or _tracked_dirty(dp_root):
        raise ValueError("fixed DP HEAD drifted or tracked worktree is dirty")
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree must be clean")
    if set(artifacts) != set(INPUT_ROLES) or set(roots) != set(INPUT_ROLES):
        raise ValueError("Fresh B2 review input role set drifted")
    canonical_artifacts = {name: Path(artifacts[name]).resolve() for name in INPUT_ROLES}
    verified_roots = _verify_inputs(canonical_artifacts, roots)

    release_root = Path(opening_release_artifact).resolve()
    verify_complete_seal(
        release_root,
        opening_release_root_sha256,
        label="Fresh B2 opening release",
    )
    if (release_root / "run.exit").read_bytes() != b"0\n":
        raise ValueError("Fresh B2 opening release did not exit successfully")
    release = validate_fresh_b2_opening_release(
        _canonical_json(release_root / "decision.json")
    )
    artifact_report = _canonical_json(execution / "artifact_report.json")
    _validate_artifact_report(
        artifact_report,
        execution=execution,
        release=release,
        release_artifact=release_root,
        release_root_sha256=opening_release_root_sha256,
        artifacts=canonical_artifacts,
        roots=verified_roots,
        probe_template=probe_template.resolve(),
        probe_template_sha256=probe_template_sha256,
    )
    consumption = validate_fresh_b2_opening_consumption(
        artifact_report["opening_consumption"],
        opening_release=release,
        release_root_sha256=opening_release_root_sha256,
    )
    marker = Path(consumption["marker_path"])
    if (
        not marker.is_file()
        or marker.is_symlink()
        or _file_sha256(marker) != consumption["marker_sha256"]
    ):
        raise ValueError("Fresh B2 opening marker drifted")
    _review_nonce_marker(
        marker,
        release=release,
        release_root_sha256=opening_release_root_sha256,
    )

    plan = validate_signal_complete_execution_plan(
        _canonical_json(canonical_artifacts["plan"] / "execution_plan.json")
    )
    route_by_identity = _route_assets(canonical_artifacts["route"])
    prepared = {
        identity["scenario_identity_sha256"]: build_signal_complete_runtime_case(
            identity,
            map_artifact=canonical_artifacts["map"],
            seeds=plan["seeds"],
        )
        for identity in plan["identities"]
    }
    preopen = _canonical_json(
        canonical_artifacts["preopen"] / "preopen_authority.json"
    )
    qualifications = preopen.get("qualification_rows")
    if type(qualifications) is not list:
        raise ValueError("Fresh B2 review qualification rows are missing")
    probe = _legacy_json_object(probe_template.resolve(), probe_template_sha256)
    selector_assets = load_v25_runtime_selector_assets(
        training_artifact=canonical_artifacts["training"],
        training_root_sha256=verified_roots["training"],
        training_review_artifact=canonical_artifacts["training_review"],
        training_review_root_sha256=verified_roots["training_review"],
    )
    selector_authority = _runtime_selector_authority(
        assets=selector_assets,
        artifacts=canonical_artifacts,
        roots=verified_roots,
        release=release,
    )
    review_report = review_fresh_b2_three_arm_execution(
        artifact=execution,
        plan=plan,
        qualification_rows=qualifications,
        probe_template=probe,
        prepared_runtime_by_scenario=prepared,
        route_asset_by_identity=route_by_identity,
        dp_repo=dp_root,
        runtime_selector_authority=selector_authority,
        opening_release=release,
        opening_release_root_sha256=opening_release_root_sha256,
        opening_consumption=consumption,
    )
    output.mkdir(parents=True)
    review_report.update(
        {
            "artifact_schema_version": SCHEMA_VERSION,
            "camp_head": _git_head(ROOT),
            "fixed_dp_head": FIXED_DP_HEAD,
            "reviewed_root_sha256": execution_seal["root_sha256"],
            "opening_release_artifact": str(release_root),
            "opening_release_root_sha256": opening_release_root_sha256,
            "opening_marker_reopened": True,
            "input_roots": verified_roots,
            "claim_authorized_by_artifact_review": False,
        }
    )
    _write_json(output / "report.json", review_report)
    (output / "HEADS").write_bytes(
        f"camp_head={review_report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n".encode(
            "ascii"
        )
    )
    (output / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(output, label="V25 Fresh B2 three-arm execution review")


def _validate_artifact_report(
    report: Mapping[str, Any],
    *,
    execution: Path,
    release: Mapping[str, Any],
    release_artifact: Path,
    release_root_sha256: str,
    artifacts: Mapping[str, Path],
    roots: Mapping[str, str],
    probe_template: Path,
    probe_template_sha256: str,
) -> None:
    fields = {
        "schema_version",
        "status",
        "camp_head",
        "fixed_dp_head",
        "device",
        "input_artifacts",
        "input_roots",
        "probe_template",
        "probe_template_sha256",
        "opening_release_artifact",
        "opening_release_root_sha256",
        "opening_consumption",
        "execution_report_sha256",
        "fresh_b2_opened_once",
        "training_executed",
        "calibration_executed",
        "claim_authorized_by_artifact",
    }
    if type(report) is not dict or set(report) != fields:
        raise ValueError("Fresh B2 artifact report field set drifted")
    expected = {
        "schema_version": EXECUTION_ARTIFACT_SCHEMA_VERSION,
        "status": "sealed_fresh_b2_execution",
        "fixed_dp_head": FIXED_DP_HEAD,
        "device": "cuda",
        "input_artifacts": {role: str(artifacts[role]) for role in INPUT_ROLES},
        "input_roots": dict(roots),
        "probe_template": str(probe_template),
        "probe_template_sha256": probe_template_sha256,
        "opening_release_root_sha256": release_root_sha256,
        "opening_release_artifact": str(release_artifact),
        "fresh_b2_opened_once": True,
        "training_executed": False,
        "calibration_executed": False,
        "claim_authorized_by_artifact": False,
    }
    if any(not _strict_equal(report.get(name), value) for name, value in expected.items()):
        raise ValueError("Fresh B2 artifact report exact contract drifted")
    if report["camp_head"] != release["pointer_head_at_release"]:
        raise ValueError("Fresh B2 artifact CAMP HEAD drifted")
    if report["execution_report_sha256"] != _canonical_sha_file(
        execution / "report.json"
    ):
        raise ValueError("Fresh B2 execution report SHA drifted")


def _review_nonce_marker(
    marker: Path,
    *,
    release: Mapping[str, Any],
    release_root_sha256: str,
) -> None:
    expected = {
        "schema_version": "camp_dp_v25_fresh_b2_opening_nonce_marker_v1",
        "gate": "fresh_b2_one_time_opening",
        "release_root_sha256": release_root_sha256,
        "run_nonce": release["run_nonce"],
        "authorized_output_dir": release["authorized_output_dir"],
        "consumed_before_outcome_capable_operation": True,
        "outcome_fields_consumed_before_nonce": [],
        "second_consumption_allowed": False,
    }
    if not _strict_equal(_canonical_json(marker), expected):
        raise ValueError("Fresh B2 opening marker exact contract drifted")


def _canonical_sha_file(path: Path) -> str:
    value = _canonical_json(path)
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--artifact-root-sha256", required=True)
    for role in INPUT_ROLES:
        option = role.replace("_", "-")
        parser.add_argument(f"--{option}-artifact", type=Path, required=True)
        parser.add_argument(f"--{option}-root-sha256", required=True)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--probe-template-sha256", required=True)
    parser.add_argument("--opening-release-artifact", type=Path, required=True)
    parser.add_argument("--opening-release-root-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    artifacts = {
        role: getattr(args, f"{role}_artifact") for role in INPUT_ROLES
    }
    roots = {
        role: getattr(args, f"{role}_root_sha256") for role in INPUT_ROLES
    }
    digest = review(
        artifact=args.artifact,
        artifact_root_sha256=args.artifact_root_sha256,
        artifacts=artifacts,
        roots=roots,
        probe_template=args.probe_template,
        probe_template_sha256=args.probe_template_sha256,
        opening_release_artifact=args.opening_release_artifact,
        opening_release_root_sha256=args.opening_release_root_sha256,
        dp_repo=args.dp_repo,
        output_dir=args.output_dir,
    )
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
