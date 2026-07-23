#!/usr/bin/env python3
"""Independently review a sealed generic holdout success or fatal execution."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
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
    review_holdout_three_arm_execution,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (  # noqa: E402
    _strict_canonical_json,
    validate_fatal_artifact,
)
from camp_core.integrations.diffusion_planner_v25_holdout_opening_rc import (  # noqa: E402
    validate_production_rc_controller_decision,
    validate_production_rc_opening_release,
)
from camp_core.integrations.diffusion_planner_v25_holdout_state import (  # noqa: E402
    validate_operational_attempt,
    validate_scientific_ledger,
)
from camp_core.integrations.diffusion_planner_v25_holdout_preopen_dispatch import (  # noqa: E402
    holdout_preopen_files,
    validate_holdout_preopen_authority,
)
from camp_core.integrations.diffusion_planner_v25_holdout_plan_dispatch import (  # noqa: E402
    NONFRESH_CANARY_SPLIT,
    validate_holdout_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    load_v25_runtime_selector_assets,
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = "camp_dp_v25_holdout_execution_review_artifact_v1"


def review(
    *,
    execution_artifact: Path,
    execution_root_sha256: str,
    controller_decision_artifact: Path,
    controller_decision_root_sha256: str,
    opening_release_artifact: Path,
    opening_release_root_sha256: str,
    probe_template: Path,
    probe_template_sha256: str,
    dp_repo: Path,
    output_dir: Path,
) -> str:
    execution = Path(execution_artifact).resolve()
    output = Path(output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
    verify_complete_seal(
        execution, execution_root_sha256, label="holdout execution"
    )
    release_root = Path(opening_release_artifact).resolve()
    controller_root = Path(controller_decision_artifact).resolve()
    verify_complete_seal(
        release_root,
        opening_release_root_sha256,
        label="holdout opening release",
    )
    verify_complete_seal(
        controller_root,
        controller_decision_root_sha256,
        label="holdout controller decision",
    )
    if (
        (release_root / "run.exit").read_bytes() != b"0\n"
        or (controller_root / "run.exit").read_bytes() != b"0\n"
    ):
        raise ValueError("holdout reviewed controller/release did not pass")
    release = validate_production_rc_opening_release(
        _canonical_json(release_root / "decision.json")
    )
    controller = validate_production_rc_controller_decision(
        _canonical_json(controller_root / "decision.json")
    )
    if (
        release["controller_decision_root_sha256"]
        != controller_decision_root_sha256
        or controller["holdout_identity"] != release["holdout_identity"]
        or controller["experiment_protocol"] != release["experiment_protocol"]
    ):
        raise ValueError("holdout reviewed controller/release drifted")
    operational = validate_operational_attempt(
        _strict_canonical_json(Path(release["operational_attempt_path"]))
    )
    scientific_path = Path(release["scientific_ledger_path"])
    scientific = (
        validate_scientific_ledger(
            _strict_canonical_json(scientific_path)
        )
        if scientific_path.exists()
        else None
    )
    run_exit = (execution / "run.exit").read_bytes()
    if run_exit == b"1\n":
        fatal = validate_fatal_artifact(
            _canonical_json(execution / "fatal.json")
        )
        if (
            (
                scientific is not None
                and (
                    scientific["state"] != "terminal_failure"
                    or scientific["terminal_artifact_root_sha256"]
                    != execution_root_sha256
                )
            )
            or (
                scientific is None
                and operational["state"] != "pre_exposure_failure"
            )
            or fatal["opening_release_root_sha256"]
            != opening_release_root_sha256
            or fatal["holdout_identity_sha256"]
            != release["holdout_identity"]["holdout_identity_sha256"]
            or fatal["experiment_protocol_sha256"]
            != release["experiment_protocol"][
                "experiment_protocol_sha256"
            ]
        ):
            raise ValueError("holdout fatal execution/tombstone drifted")
        result = {
            "schema_version": SCHEMA_VERSION,
            "status": "passed_independent_holdout_artifact_fatal_review",
            "reviewed_root_sha256": execution_root_sha256,
            "opening_release_root_sha256": opening_release_root_sha256,
            "holdout_identity_sha256": fatal["holdout_identity_sha256"],
            "planned_arm_run_count": fatal["planned_arm_run_count"],
            "attempted_arm_run_count": fatal["attempted_arm_run_count"],
            "complete_arm_run_count": fatal["complete_arm_run_count"],
            "unattempted_arm_run_count": fatal[
                "unattempted_arm_run_count"
            ],
            "full_denominator_formed": False,
            "fresh_outcome_evaluated": False,
            "claim_authorized_by_review": False,
        }
    elif run_exit == b"0\n":
        if (
            scientific is None
            or scientific["state"] != "full_denominator_formed"
            or scientific["terminal_artifact_root_sha256"] is not None
        ):
            raise ValueError("holdout success execution/tombstone drifted")
        preopen_root = Path(release["preopen_authority"]["path"]).resolve()
        verify_complete_seal(
            preopen_root,
            release["preopen_authority"]["root_sha256"],
            label="holdout reviewed preopen",
        )
        if (preopen_root / "run.exit").read_bytes() != b"0\n":
            raise ValueError("holdout reviewed preopen did not pass")
        preopen = validate_holdout_preopen_authority(
            _canonical_json(preopen_root / "preopen_authority.json")
        )
        sealed_bindings = dict(preopen["upstream_bindings"])
        if preopen["holdout_identity"]["split"] == NONFRESH_CANARY_SPLIT:
            sealed_bindings.update(preopen["source_fixture_bindings"])
        for role, binding in sealed_bindings.items():
            upstream = Path(binding["path"]).resolve()
            verify_complete_seal(
                upstream,
                binding["root_sha256"],
                label=f"reviewed holdout upstream {role}",
            )
            if (upstream / "run.exit").read_bytes() != b"0\n":
                raise ValueError(f"reviewed holdout upstream failed: {role}")
        preopen_files = holdout_preopen_files(
            preopen["holdout_identity"]["split"]
        )
        plan = validate_holdout_execution_plan(
            _canonical_json(preopen_root / preopen_files["plan"])
        )
        prepared_rows = _canonical_value(
            preopen_root / preopen_files["prepared_runtime"]
        )
        prepared = {
            row["scenario_identity_sha256"]: row for row in prepared_rows
        }
        route_manifest = _canonical_json(
            preopen_root / preopen_files["route_assets"]
        )
        route_by_identity = {
            row["route_identity_sha256"]: row["route_asset"]
            for row in route_manifest["route_assets"]
        }
        bindings = preopen["upstream_bindings"]
        training = Path(bindings["training"]["path"]).resolve()
        training_review = Path(bindings["training_review"]["path"]).resolve()
        assets = load_v25_runtime_selector_assets(
            training_artifact=training,
            training_root_sha256=bindings["training"]["root_sha256"],
            training_review_artifact=training_review,
            training_review_root_sha256=bindings["training_review"][
                "root_sha256"
            ],
        )
        selector = _independent_runtime_selector_authority(
            assets=assets,
            training=training,
            training_review=training_review,
            bindings=bindings,
            release=release,
        )
        artifact_report = _canonical_json(
            execution / "artifact_report.json"
        )
        consumption = artifact_report["opening_consumption"]
        independent = review_holdout_three_arm_execution(
            artifact=execution,
            plan=plan,
            qualification_rows=preopen["runtime_qualification_rows"],
            probe_template=_legacy_json_object(
                Path(probe_template).resolve(), probe_template_sha256
            ),
            prepared_runtime_by_scenario=prepared,
            route_asset_by_identity=route_by_identity,
            dp_repo=Path(dp_repo).resolve(),
            runtime_selector_authority=selector,
            opening_release=release,
            opening_release_root_sha256=opening_release_root_sha256,
            opening_consumption=consumption,
        )
        result = {
            "schema_version": SCHEMA_VERSION,
            "status": "passed_independent_holdout_execution_review",
            "reviewed_root_sha256": execution_root_sha256,
            "opening_release_root_sha256": opening_release_root_sha256,
            "holdout_identity_sha256": release["holdout_identity"][
                "holdout_identity_sha256"
            ],
            "experiment_protocol_sha256": release[
                "experiment_protocol"
            ]["experiment_protocol_sha256"],
            "independent_execution_review": independent,
            "full_denominator_formed": True,
            "fresh_outcome_evaluated": False,
            "claim_authorized_by_review": False,
        }
    else:
        raise ValueError("holdout execution run.exit drifted")
    output.mkdir(parents=True)
    _write_json(output / "report.json", result)
    (output / "HEADS").write_bytes(
        (
            f"camp_head={release['pointer_head_at_release']}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (output / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode("utf-8"))
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(output, label="independent V25 holdout execution review")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-artifact", type=Path, required=True)
    parser.add_argument("--execution-root-sha256", required=True)
    parser.add_argument("--controller-decision-artifact", type=Path, required=True)
    parser.add_argument("--controller-decision-root-sha256", required=True)
    parser.add_argument("--opening-release-artifact", type=Path, required=True)
    parser.add_argument("--opening-release-root-sha256", required=True)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--probe-template-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    root = review(**vars(_arguments()))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))
    return 0


def _independent_runtime_selector_authority(
    *,
    assets: Any,
    training: Path,
    training_review: Path,
    bindings: Mapping[str, Mapping[str, str]],
    release: Mapping[str, Any],
) -> dict[str, Any]:
    protocol = release["experiment_protocol"]
    authority = {
        "training_artifact": dict(bindings["training"]),
        "training_review_artifact": dict(bindings["training_review"]),
        "calibration_contract_root_sha256": bindings[
            "calibration_freeze"
        ]["root_sha256"],
        "preopen_qualification_root_sha256": release[
            "preopen_authority"
        ]["root_sha256"],
        "scenario_manifest_root_sha256": release["holdout_identity"][
            "scenario_manifest_sha256"
        ],
        "model_registry_sha256": _file_sha256(
            training / "model_registry.json"
        ),
        "training_scale_sha256": assets.atom_scales_sha256,
        "context_scaler_sha256": (
            assets.scene14d_weight_provider.context_scaler_sha256
        ),
        "atom_scales": {
            "path": str(training / "runtime_atom_scales.json"),
            "sha256": assets.atom_scales_sha256,
        },
        "static14d_weights": {
            "path": str(training / "static14d_runtime_weights.npy"),
            "sha256": assets.static14d_weights_sha256,
        },
    }
    if any(
        authority[name] != protocol[name]
        for name in (
            "model_registry_sha256",
            "training_scale_sha256",
            "context_scaler_sha256",
        )
    ):
        raise ValueError("reviewed holdout runtime assets differ from protocol")
    return authority


def _canonical_json(path: Path) -> dict[str, Any]:
    value = _canonical_value(path)
    if type(value) is not dict:
        raise ValueError(f"reviewed holdout JSON is not an object: {path}")
    return value


def _canonical_value(path: Path) -> Any:
    raw = Path(path).read_bytes()
    value = _strict_parse_json(raw, path)
    if raw != _canonical_bytes(value):
        raise ValueError(f"reviewed holdout JSON is not canonical: {path}")
    return value


def _legacy_json_object(path: Path, expected_sha256: str) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    if _file_sha256(path) != expected_sha256:
        raise ValueError("reviewed holdout probe template SHA256 drifted")
    value = _strict_parse_json(raw, path)
    if type(value) is not dict:
        raise ValueError("reviewed holdout probe template is not an object")
    return value


def _strict_parse_json(raw: bytes, path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    return json.loads(
        raw.decode("utf-8", "strict"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {path}: {token}")
        ),
    )


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
