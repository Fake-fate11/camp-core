#!/usr/bin/env python3
"""Run and seal the exact non-Fresh production-composition preflight for B3."""

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

from camp_core.integrations.diffusion_planner_artifact_seal import (
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_b3_preopen import (
    FIXED_DP_HEAD,
    build_b3_experiment_protocol,
    build_b3_holdout_identity,
)
from camp_core.integrations.diffusion_planner_v25_holdout_contract import (
    canonical_json_bytes,
)
from camp_core.integrations.diffusion_planner_v25_holdout_execution import (
    freeze_holdout_arm_config_from_legacy,
)
from camp_core.integrations.diffusion_planner_v25_holdout_preflight import (
    freeze_nonfresh_preflight_authority,
    project_actual_native_preflight_callbacks,
    run_production_composition_preflight,
)
from camp_core.integrations.diffusion_planner_v25_holdout_protocol import (
    derive_protocol_assets_from_accepted_preopen,
    load_accepted_preopen_authority,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (
    load_v25_runtime_selector_assets,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_execution import (
    build_fresh_b2_arm_config,
    validate_paired_calibration_arm_config,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (
    build_signal_complete_suite,
    validate_signal_complete_suite,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (
    build_signal_complete_execution_plan,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
    build_native_arm_runner,
)


SCHEMA_VERSION = "camp_dp_v25_fresh_b3_production_preflight_artifact_v2"
PLAN_ARMS = {
    "candidate0": "candidate0_operational_default",
    "static14d": "camp_static14d",
    "scene14d": "camp_scene14d_no_v2i",
}


def build(
    *,
    accepted_preopen_artifact: Path,
    accepted_preopen_root_sha256: str,
    accepted_preopen_review_artifact: Path,
    accepted_preopen_review_root_sha256: str,
    output_dir: Path,
) -> str:
    if _tracked_dirty():
        raise ValueError("CAMP tracked worktree must be clean")
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    accepted_preopen, _ = load_accepted_preopen_authority(
        preopen_artifact=accepted_preopen_artifact,
        preopen_root_sha256=accepted_preopen_root_sha256,
        preopen_review_artifact=accepted_preopen_review_artifact,
        preopen_review_root_sha256=accepted_preopen_review_root_sha256,
    )
    protocol_assets, protocol_receipt = (
        derive_protocol_assets_from_accepted_preopen(
            preopen_artifact=accepted_preopen_artifact,
            preopen_root_sha256=accepted_preopen_root_sha256,
            preopen_review_artifact=accepted_preopen_review_artifact,
            preopen_review_root_sha256=accepted_preopen_review_root_sha256,
        )
    )
    fixture = _accepted_calibration_fixture(accepted_preopen)
    legacy_fixture_configs = _load_fixture_configs(
        fixture_artifact=Path(fixture["artifact"]["path"]),
        fixture_root_sha256=fixture["artifact"]["root_sha256"],
    )
    suite = build_signal_complete_suite("fresh_b3")
    suite_receipt = validate_signal_complete_suite(suite)
    plan = build_signal_complete_execution_plan("fresh_b3")
    identity = build_b3_holdout_identity(suite=suite, plan=plan)
    protocol = build_b3_experiment_protocol(protocol_assets)
    fresh_selector = _fresh_runtime_selector_authority(
        accepted_preopen=accepted_preopen,
        accepted_preopen_root_sha256=accepted_preopen_root_sha256,
        b3_execution_plan_sha256=identity["execution_plan_sha256"],
        calibration_selector=legacy_fixture_configs["candidate0"][
            "runtime_selector_authority"
        ],
    )
    configs = {}
    for arm, plan_arm in PLAN_ARMS.items():
        fixture_config = legacy_fixture_configs[arm]
        legacy = build_fresh_b2_arm_config(
            probe_template=fixture_config,
            prepared_runtime=fixture_config["signal_complete_runtime"],
            execution_unit=_fixture_execution_unit(fixture_config),
            plan_arm=plan_arm,
            route_asset=fixture_config["routes"][0],
            dp_repo=Path(fixture_config["fixed_dp"]["repo"]),
            runtime_selector_authority=fresh_selector,
        )
        configs[arm] = freeze_holdout_arm_config_from_legacy(
            legacy_config=legacy,
            holdout_identity=identity,
            experiment_protocol=protocol,
        )
    authority = freeze_nonfresh_preflight_authority(
        holdout_identity_sha256=identity["holdout_identity_sha256"],
        experiment_protocol_sha256=protocol["experiment_protocol_sha256"],
        fixture_artifact_root_sha256=fixture["artifact"]["root_sha256"],
        fixture_recovery_root_sha256=fixture["recovery"]["root_sha256"],
        fixture_recovery_review_root_sha256=fixture["review"][
            "root_sha256"
        ],
    )
    training = protocol_receipt["accepted_training"]
    training_review = protocol_receipt["accepted_training_review"]
    selector_assets = load_v25_runtime_selector_assets(
        training_artifact=Path(training["path"]),
        training_root_sha256=training["root_sha256"],
        training_review_artifact=Path(training_review["path"]),
        training_review_root_sha256=training_review["root_sha256"],
    )

    output.mkdir(parents=True)
    try:
        _write(output / "b3_map_suite.json", suite_receipt)
        _write(output / "b3_execution_plan.json", plan)
        _write(output / "holdout_identity.json", identity)
        _write(output / "experiment_protocol.json", protocol)
        _write(output / "protocol_assets.json", protocol_assets)
        _write(output / "protocol_assets_receipt.json", protocol_receipt)
        _write(output / "nonfresh_preflight_authority.json", authority)
        _write(output / "fixture_binding.json", fixture)
        config_root = output / "configs"
        config_root.mkdir()
        for arm, config in configs.items():
            _write(config_root / f"{arm}.json", config)

        primary: dict[str, dict[str, Any]] = {}
        for arm, plan_arm in PLAN_ARMS.items():
            run_dir = output / "runs" / arm
            run_dir.mkdir(parents=True)
            runner = build_native_arm_runner(
                configs[arm],
                device="cuda",
                holdout_preflight_authority=authority,
            )
            snapshots: list[dict[str, Any]] = []
            primary[arm] = dict(
                runner(
                    route=configs[arm]["routes"][0],
                    arm=("dp" if arm == "candidate0" else "camp"),
                    config=configs[arm],
                    output_dir=run_dir / "native",
                    max_steps=64,
                    fixed_k8_candidate0=(arm == "candidate0"),
                    v25_weight_provider=(
                        selector_assets.scene14d_weight_provider
                        if arm == "scene14d"
                        else None
                    ),
                    decision_sink=(
                        snapshots.append if arm != "candidate0" else None
                    ),
                )
            )
            expected_snapshots = 0 if arm == "candidate0" else 64
            if len(snapshots) != expected_snapshots:
                raise ValueError(
                    f"{plan_arm} production preflight snapshot count drifted"
                )
            _write(run_dir / "native_receipt.json", primary[arm])
            _write(run_dir / "decision_evidence.json", snapshots)

        diagnostic_config = legacy_fixture_configs["candidate0"]
        diagnostic_dir = output / "runs" / "candidate0_supplementary"
        diagnostic_dir.mkdir()
        diagnostic_runner = build_native_arm_runner(
            diagnostic_config, device="cuda"
        )
        diagnostic = dict(
            diagnostic_runner(
                route=diagnostic_config["routes"][0],
                arm="dp",
                config=diagnostic_config,
                output_dir=diagnostic_dir / "native",
                max_steps=64,
                fixed_k8_candidate0=True,
            )
        )
        _write(diagnostic_dir / "native_receipt.json", diagnostic)
        callbacks = project_actual_native_preflight_callbacks(
            config_payloads=configs,
            primary_native_receipts=primary,
            candidate0_supplementary_native_receipt=diagnostic,
        )

        def callback(
            config: Mapping[str, Any], tick_index: int
        ) -> Mapping[str, Any]:
            arm = config["protocol"]["holdout_opening_arm"]
            return callbacks[arm][tick_index]

        preflight = run_production_composition_preflight(
            holdout_identity=identity,
            experiment_protocol=protocol,
            nonfresh_preflight_authority=authority,
            fixture_root_sha256=fixture["artifact"]["root_sha256"],
            config_payloads=configs,
            native_callback=callback,
        )
        _write(output / "preflight.json", preflight)
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": "passed_fresh_b3_nonfresh_exact_production_preflight",
            "camp_head": _git_head(),
            "fixed_dp_head": FIXED_DP_HEAD,
            "fixture": fixture,
            "holdout_identity_sha256": identity["holdout_identity_sha256"],
            "experiment_protocol_sha256": protocol[
                "experiment_protocol_sha256"
            ],
            "paired_unit_count": 1,
            "arm_run_count": 3,
            "tick_count": 192,
            "candidate0_action_first": True,
            "candidate0_pool_evidence_post_action": True,
            "same_forward_claimed_for_supplementary_pool": False,
            "real_native_callback_executed": True,
            "fixed_dp_forward_executed_on_nonfresh_fixture": True,
            "fresh_b3_opened": False,
            "outcome_fields_consumed": [],
        }
        _write(output / "report.json", report)
        _write_controls(output, exit_code=0)
        return seal_artifact(
            output, label="V25 Fresh B3 non-Fresh production preflight"
        )
    except BaseException as exc:
        _write(
            output / "failure.json",
            {
                "schema_version": SCHEMA_VERSION,
                "status": "failed_fresh_b3_nonfresh_production_preflight",
                "reason": str(exc),
                "fresh_b3_opened": False,
                "outcome_fields_consumed": [],
            },
        )
        _write_controls(output, exit_code=1)
        seal_artifact(output, label="failed V25 Fresh B3 production preflight")
        raise


def _accepted_calibration_fixture(
    accepted_preopen: Mapping[str, Any],
) -> dict[str, dict[str, str]]:
    bindings = accepted_preopen["upstream_bindings"]
    recovery = _binding(bindings, "calibration_recovery")
    review = _binding(bindings, "calibration_recovery_review")
    verify_complete_seal(
        Path(recovery["path"]),
        recovery["root_sha256"],
        label="accepted calibration recovery",
    )
    verify_complete_seal(
        Path(review["path"]),
        review["root_sha256"],
        label="accepted calibration recovery review",
    )
    report = _canonical_object(Path(review["path"]) / "report.json")
    if (
        report.get("status")
        != "passed_independent_paired_calibration_recovery_review"
        or report.get("reviewed_recovery_root_sha256")
        != recovery["root_sha256"]
    ):
        raise ValueError("accepted calibration recovery review drifted")
    artifact = {
        "path": str(Path(report["original_execution_artifact"]).resolve()),
        "root_sha256": report["original_execution_root_sha256"],
    }
    verify_complete_seal(
        Path(artifact["path"]),
        artifact["root_sha256"],
        label="accepted immutable calibration raw fixture",
    )
    return {"artifact": artifact, "recovery": recovery, "review": review}


def _load_fixture_configs(
    *, fixture_artifact: Path, fixture_root_sha256: str
) -> dict[str, dict[str, Any]]:
    seal = verify_complete_seal(
        fixture_artifact,
        fixture_root_sha256,
        label="accepted immutable calibration raw fixture",
    )
    candidates = sorted(
        relative
        for relative in seal["manifest_paths"]
        if relative.startswith("runs/")
        and relative.endswith("/run_config.json")
        and relative.split("/")[1].startswith(("0000_", "0001_", "0002_"))
    )
    if len(candidates) != 3:
        raise ValueError("calibration fixture unit-zero config inventory drifted")
    result: dict[str, dict[str, Any]] = {}
    unit_sha: str | None = None
    for relative in candidates:
        config = validate_paired_calibration_arm_config(
            _canonical_object(fixture_artifact / relative)
        )
        plan = config["signal_complete_plan_authority"]
        if plan["unit_ordinal"] != 0:
            raise ValueError("calibration fixture did not select unit ordinal zero")
        if unit_sha is None:
            unit_sha = plan["unit_sha256"]
        elif plan["unit_sha256"] != unit_sha:
            raise ValueError("calibration fixture paired unit drifted")
        arm = {
            "candidate0_operational_default": "candidate0",
            "camp_static14d": "static14d",
            "camp_scene14d_no_v2i": "scene14d",
        }[plan["plan_arm"]]
        if arm in result:
            raise ValueError("calibration fixture arm duplicated")
        result[arm] = config
    if set(result) != set(PLAN_ARMS):
        raise ValueError("calibration fixture three-arm composition drifted")
    return result


def _fresh_runtime_selector_authority(
    *,
    accepted_preopen: Mapping[str, Any],
    accepted_preopen_root_sha256: str,
    b3_execution_plan_sha256: str,
    calibration_selector: Mapping[str, Any],
) -> dict[str, Any]:
    result = dict(calibration_selector)
    result["calibration_contract_root_sha256"] = _binding(
        accepted_preopen["upstream_bindings"], "calibration_freeze"
    )["root_sha256"]
    result["preopen_qualification_root_sha256"] = (
        accepted_preopen_root_sha256
    )
    if (
        type(b3_execution_plan_sha256) is not str
        or len(b3_execution_plan_sha256) != 64
        or set(b3_execution_plan_sha256) - set("0123456789abcdef")
    ):
        raise ValueError("Fresh B3 execution-plan SHA drifted")
    result["scenario_manifest_root_sha256"] = b3_execution_plan_sha256
    return result


def _fixture_execution_unit(
    config: Mapping[str, Any],
) -> dict[str, Any]:
    plan = config.get("signal_complete_plan_authority")
    if type(plan) is not dict:
        raise ValueError("calibration fixture plan authority is missing")
    fields = (
        "unit_ordinal",
        "scenario_identity_sha256",
        "seed",
        "ordered_arms",
        "unit_sha256",
    )
    if any(name not in plan for name in fields):
        raise ValueError("calibration fixture paired-unit authority drifted")
    return {name: plan[name] for name in fields}


def _binding(
    bindings: Mapping[str, Any], name: str
) -> dict[str, str]:
    value = bindings.get(name)
    if type(value) is not dict or set(value) != {"path", "root_sha256"}:
        raise ValueError(f"accepted pre-open {name} binding drifted")
    return {
        "path": str(Path(value["path"]).resolve()),
        "root_sha256": value["root_sha256"],
    }


def _write(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes(value))


def _write_controls(root: Path, *, exit_code: int) -> None:
    (root / "HEADS").write_bytes(
        (
            f"camp_head={_git_head()}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n"
        ).encode("ascii")
    )
    (root / "COMMAND").write_bytes(
        (" ".join(sys.argv) + "\n").encode("utf-8")
    )
    (root / "run.exit").write_bytes(f"{exit_code}\n".encode("ascii"))


def _canonical_object(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path}: {key}")
            result[key] = value
        return result

    value = json.loads(
        raw.decode("utf-8", "strict"),
        object_pairs_hook=pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"nonfinite JSON token in {path}: {token}")
        ),
    )
    if type(value) is not dict or raw != canonical_json_bytes(value):
        raise ValueError(f"authority JSON is not canonical: {path}")
    return value


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
    parser.add_argument(
        "--accepted-preopen-artifact", type=Path, required=True
    )
    parser.add_argument("--accepted-preopen-root-sha256", required=True)
    parser.add_argument(
        "--accepted-preopen-review-artifact", type=Path, required=True
    )
    parser.add_argument(
        "--accepted-preopen-review-root-sha256", required=True
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = build(
        accepted_preopen_artifact=args.accepted_preopen_artifact,
        accepted_preopen_root_sha256=args.accepted_preopen_root_sha256,
        accepted_preopen_review_artifact=args.accepted_preopen_review_artifact,
        accepted_preopen_review_root_sha256=(
            args.accepted_preopen_review_root_sha256
        ),
        output_dir=args.output_dir,
    )
    print(root)


if __name__ == "__main__":
    main()
