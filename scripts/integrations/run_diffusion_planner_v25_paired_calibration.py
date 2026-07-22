#!/usr/bin/env python3
"""Run and seal the Fresh-closed V25 100-pair/300-arm calibration."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_calibration_preregistration import (  # noqa: E402
    validate_paired_calibration_preregistration,
)
from camp_core.integrations.diffusion_planner_v25_calibration_analysis import (  # noqa: E402
    analyze_paired_calibration_outcomes,
)
from camp_core.integrations.diffusion_planner_v25_calibration_atoms import (  # noqa: E402
    analyze_calibration_decision_evidence,
)
from camp_core.integrations.diffusion_planner_v25_paired_calibration import (  # noqa: E402
    validate_paired_calibration_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_paired_calibration_execution import (  # noqa: E402
    execute_paired_calibration_units,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    V25RuntimeSelectorAssets,
    load_v25_runtime_selector_assets,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (  # noqa: E402
    validate_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (  # noqa: E402
    build_signal_complete_runtime_case,
)
from scripts.integrations.run_diffusion_planner_v25_candidate0_calibration import (  # noqa: E402
    TRAIN_LOCK,
    _bind_reviewed_runtime_receipts,
    _canonical_json,
    _canonical_value,
    _exclusive_lock,
    _legacy_json_object,
    _preconditions,
    _sha256,
    _verify_inputs,
    _write_control_files,
    _write_json,
)


SCHEMA_VERSION = "camp_dp_v25_paired_calibration_execution_artifact_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
RunOne = Callable[[Mapping[str, Any], Path, str], Mapping[str, Any]]


def run(
    *,
    plan_artifact: Path,
    plan_root_sha256: str,
    map_artifact: Path,
    map_root_sha256: str,
    route_artifact: Path,
    route_root_sha256: str,
    route_review_artifact: Path,
    route_review_root_sha256: str,
    runtime_artifact: Path,
    runtime_root_sha256: str,
    runtime_review_artifact: Path,
    runtime_review_root_sha256: str,
    paired_plan_artifact: Path,
    paired_plan_root_sha256: str,
    paired_plan_review_artifact: Path,
    paired_plan_review_root_sha256: str,
    preregistration_artifact: Path,
    preregistration_root_sha256: str,
    preregistration_review_artifact: Path,
    preregistration_review_root_sha256: str,
    training_artifact: Path,
    training_root_sha256: str,
    training_review_artifact: Path,
    training_review_root_sha256: str,
    probe_template: Path,
    probe_template_sha256: str,
    dp_repo: Path,
    output_dir: Path,
    device: str,
    run_one: RunOne | None = None,
) -> str:
    if device != "cuda":
        raise ValueError("paired calibration production execution requires cuda")
    dp_root = dp_repo.resolve()
    output = output_dir.resolve()
    _preconditions(dp_root, output)
    roots = _verify_inputs(
        plan_artifact=plan_artifact,
        plan_root_sha256=plan_root_sha256,
        map_artifact=map_artifact,
        map_root_sha256=map_root_sha256,
        route_artifact=route_artifact,
        route_root_sha256=route_root_sha256,
        route_review_artifact=route_review_artifact,
        route_review_root_sha256=route_review_root_sha256,
        runtime_artifact=runtime_artifact,
        runtime_root_sha256=runtime_root_sha256,
        runtime_review_artifact=runtime_review_artifact,
        runtime_review_root_sha256=runtime_review_root_sha256,
    )
    extras = {
        "paired_plan": (paired_plan_artifact, paired_plan_root_sha256),
        "paired_plan_review": (
            paired_plan_review_artifact,
            paired_plan_review_root_sha256,
        ),
        "preregistration": (
            preregistration_artifact,
            preregistration_root_sha256,
        ),
        "preregistration_review": (
            preregistration_review_artifact,
            preregistration_review_root_sha256,
        ),
        "training": (training_artifact, training_root_sha256),
        "training_review": (training_review_artifact, training_review_root_sha256),
    }
    for role, (artifact, digest) in extras.items():
        resolved = Path(artifact).resolve()
        seal = verify_complete_seal(resolved, digest, label=f"paired calibration {role}")
        if (resolved / "run.exit").read_bytes() != b"0\n":
            raise ValueError(f"paired calibration {role} run.exit drifted")
        roots[f"{role}_artifact"] = str(resolved)
        roots[f"{role}_root_sha256"] = seal["root_sha256"]

    base = validate_signal_complete_execution_plan(
        _canonical_json(Path(roots["plan_artifact"]) / "execution_plan.json")
    )
    paired = validate_paired_calibration_execution_plan(
        _canonical_json(
            Path(roots["paired_plan_artifact"]) / "paired_calibration_plan.json"
        ),
        calibration_plan=base,
    )
    paired_review = _canonical_json(
        Path(roots["paired_plan_review_artifact"]) / "report.json"
    )
    preregistration = validate_paired_calibration_preregistration(
        _canonical_json(
            Path(roots["preregistration_artifact"]) / "preregistration.json"
        )
    )
    prereg_review = _canonical_json(
        Path(roots["preregistration_review_artifact"]) / "report.json"
    )
    if (
        paired_review.get("status")
        != "passed_independent_paired_calibration_plan_review"
        or paired_review.get("reviewed_root_sha256")
        != roots["paired_plan_root_sha256"]
        or prereg_review.get("status")
        != "passed_independent_paired_calibration_preregistration_review"
        or prereg_review.get("reviewed_root_sha256")
        != roots["preregistration_root_sha256"]
        or preregistration.get("fresh_b2_opened") is not False
        or preregistration.get("fresh_open_authorized") is not False
    ):
        raise ValueError("paired calibration plan/preregistration review drifted")
    _bind_preregistration_roots(preregistration, roots)

    probe = _legacy_json_object(probe_template, probe_template_sha256)
    route_manifest = _canonical_json(
        Path(roots["route_artifact"]) / "route_assets.json"
    )
    route_rows = route_manifest.get("route_assets")
    if type(route_rows) is not list:
        raise ValueError("paired calibration route inventory is malformed")
    route_by_identity = {
        row["route_identity_sha256"]: dict(row["route_asset"])
        for row in route_rows
    }
    prepared = {
        identity["scenario_identity_sha256"]: build_signal_complete_runtime_case(
            identity,
            map_artifact=Path(roots["map_artifact"]),
            seeds=base["seeds"],
        )
        for identity in base["identities"]
    }
    runtime_receipts = _bind_reviewed_runtime_receipts(
        plan=base,
        prepared_runtime_by_scenario=prepared,
        runtime_artifact=Path(roots["runtime_artifact"]),
    )
    assets = load_v25_runtime_selector_assets(
        training_artifact=Path(roots["training_artifact"]),
        training_root_sha256=roots["training_root_sha256"],
        training_review_artifact=Path(roots["training_review_artifact"]),
        training_review_root_sha256=roots["training_review_root_sha256"],
    )
    selector_authority = _selector_authority(assets, roots)
    if selector_authority != {
        "training_artifact": preregistration["root_artifacts"]["training"],
        "training_review_artifact": preregistration["root_artifacts"][
            "training_review"
        ],
        "model_registry_sha256": preregistration["model_authority"][
            "model_registry_sha256"
        ],
        "training_scale_sha256": preregistration["model_authority"][
            "training_scale_sha256"
        ],
        "context_scaler_sha256": preregistration["model_authority"][
            "context_scaler_sha256"
        ],
        "atom_scales": selector_authority["atom_scales"],
        "static14d_weights": selector_authority["static14d_weights"],
    } or (
        assets.atom_scales_sha256
        != preregistration["model_authority"]["atom_scales_file_sha256"]
        or assets.static14d_weights_sha256
        != preregistration["model_authority"]["static14d_weights_file_sha256"]
        or assets.scene14d_weight_provider.theta_sha256
        != preregistration["model_authority"]["scene14d_theta_sha256"]
    ):
        raise ValueError("paired calibration runtime model authority drifted")
    production_run = run_one or _native_run_one(device=device, assets=assets)

    with _exclusive_lock(TRAIN_LOCK):
        try:
            report = execute_paired_calibration_units(
                calibration_plan=base,
                paired_plan=paired,
                probe_template=probe,
                prepared_runtime_by_scenario=prepared,
                route_asset_by_identity=route_by_identity,
                runtime_selector_authority=selector_authority,
                dp_repo=dp_root,
                output_dir=output,
                run_one=production_run,
                progress_sink=_progress_sink(output),
            )
            corpus = _canonical_json(output / "paired_calibration_corpus.json")
            analysis = analyze_paired_calibration_outcomes(corpus)
            atom_calibration = analyze_calibration_decision_evidence(
                camp_runs=_camp_decision_runs(output=output, corpus=corpus),
                atom_scales=assets.atom_scales,
                static14d_weights=assets.static14d_weights,
                scene14d_provider=assets.scene14d_weight_provider,
                training_artifact=Path(roots["training_artifact"]),
            )
            _write_json(output / "calibration_analysis.json", analysis)
            _write_json(output / "atom_calibration.json", atom_calibration)
            report.update(
                {
                    "artifact_schema_version": SCHEMA_VERSION,
                    "camp_head": _git_head(ROOT),
                    "device": device,
                    "input_roots": roots,
                    "probe_template": str(probe_template.resolve()),
                    "probe_template_sha256": probe_template_sha256,
                    "runtime_receipt_sha256_by_scenario": runtime_receipts,
                    "runtime_selector_authority": selector_authority,
                    "preregistration_root_sha256": roots[
                        "preregistration_root_sha256"
                    ],
                    "calibration_analysis_sha256": _sha256(
                        output / "calibration_analysis.json"
                    ),
                    "atom_calibration_sha256": _sha256(
                        output / "atom_calibration.json"
                    ),
                    "model_loaded": run_one is None,
                    "candidate_generation_executed": run_one is None,
                    "independent_review_completed": False,
                    "fresh_b2_opened": False,
                    "fresh_outcome_fields_consumed": [],
                }
            )
            _write_json(output / "report.json", report)
            _write_control_files(output, exit_code=0)
            return seal_artifact(output, label="V25 paired calibration execution")
        except BaseException as exc:
            if output.exists():
                _write_json(
                    output / "failure.json",
                    {
                        "schema_version": SCHEMA_VERSION,
                        "status": "failed_closed_paired_calibration_execution",
                        "reason": str(exc),
                        "fresh_b2_opened": False,
                        "outcome_fields_consumed": [],
                    },
                )
                _write_control_files(output, exit_code=1)
                seal_artifact(output, label="failed V25 paired calibration execution")
            raise


def _native_run_one(*, device: str, assets: V25RuntimeSelectorAssets) -> RunOne:
    holder: dict[str, Any] = {}

    def execute(
        config: Mapping[str, Any], run_dir: Path, plan_arm: str
    ) -> Mapping[str, Any]:
        if "run_arm" not in holder:
            from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (
                build_native_arm_runner,
            )

            holder["run_arm"] = build_native_arm_runner(config, device=device)
        snapshots: list[dict[str, Any]] = []
        native_arm = "dp" if plan_arm == "candidate0_operational_default" else "camp"
        receipt = dict(
            holder["run_arm"](
                route=config["routes"][0],
                arm=native_arm,
                config=config,
                output_dir=run_dir / "native",
                max_steps=64,
                decision_sink=(snapshots.append if native_arm == "camp" else None),
                v25_weight_provider=(
                    assets.scene14d_weight_provider
                    if plan_arm == "camp_scene14d_no_v2i"
                    else None
                ),
                fixed_k8_candidate0=(plan_arm == "candidate0_operational_default"),
            )
        )
        expected_count = 0 if native_arm == "dp" else 64
        if len(snapshots) != expected_count or (
            snapshots
            and [row["sidecar"]["tick_index"] for row in snapshots]
            != list(range(64))
        ):
            raise ValueError("paired calibration decision evidence count drifted")
        evidence_path = run_dir / "decision_evidence.json"
        _write_json(evidence_path, snapshots)
        receipt["calibration_decision_evidence_sha256"] = _sha256(evidence_path)
        receipt["calibration_decision_evidence_count"] = len(snapshots)
        return receipt

    return execute


def _camp_decision_runs(
    *, output: Path, corpus: Mapping[str, Any]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in corpus["arm_results"]:
        if (
            row["status"] != "complete"
            or row["plan_arm"] == "candidate0_operational_default"
        ):
            continue
        run_dir = output / "runs" / (
            f"{row['run_ordinal']:04d}_{row['unit_ordinal']:04d}_"
            f"{row['arm_order_index']}_{row['plan_arm']}"
        )
        evidence_path = run_dir / "decision_evidence.json"
        evidence = _canonical_value(evidence_path)
        native = row["native_receipt"]
        if (
            type(evidence) is not list
            or native.get("calibration_decision_evidence_sha256")
            != _sha256(evidence_path)
            or native.get("calibration_decision_evidence_count") != len(evidence)
        ):
            raise ValueError("paired calibration decision evidence binding drifted")
        result.append(
            {
                "plan_arm": row["plan_arm"],
                "snapshots": evidence,
                "native_ticks": native["ticks"],
                "scenario_family": row["scenario_family"],
                "risk_tier": row["risk_tier"],
                "signal_source_class": row["signal_source_class"],
            }
        )
    return result


def _progress_sink(output: Path) -> Callable[[Mapping[str, Any]], None]:
    def write(value: Mapping[str, Any]) -> None:
        temporary = output / "progress.json.tmp"
        final = output / "progress.json"
        _write_json(temporary, dict(value))
        temporary.replace(final)

    return write


def _selector_authority(
    assets: V25RuntimeSelectorAssets, roots: Mapping[str, str]
) -> dict[str, Any]:
    training = Path(roots["training_artifact"])
    return {
        "training_artifact": {
            "path": roots["training_artifact"],
            "root_sha256": roots["training_root_sha256"],
        },
        "training_review_artifact": {
            "path": roots["training_review_artifact"],
            "root_sha256": roots["training_review_root_sha256"],
        },
        "model_registry_sha256": _sha256(training / "model_registry.json"),
        "training_scale_sha256": assets.atom_scales_sha256,
        "context_scaler_sha256": assets.scene14d_weight_provider.context_scaler_sha256,
        "atom_scales": {
            "path": str((training / "runtime_atom_scales.json").resolve()),
            "sha256": assets.atom_scales_sha256,
        },
        "static14d_weights": {
            "path": str((training / "static14d_runtime_weights.npy").resolve()),
            "sha256": assets.static14d_weights_sha256,
        },
    }


def _bind_preregistration_roots(
    preregistration: Mapping[str, Any], roots: Mapping[str, str]
) -> None:
    mapping = {
        "training": "training",
        "training_review": "training_review",
        "map": "map",
        "map_review": "map_review",
        "base_plan": "plan",
        "base_plan_review": "plan_review",
        "paired_plan": "paired_plan",
        "paired_plan_review": "paired_plan_review",
        "route": "route",
        "route_review": "route_review",
        "runtime": "runtime",
        "runtime_review": "runtime_review",
    }
    bound = preregistration["root_artifacts"]
    for prereg_role, runtime_role in mapping.items():
        if runtime_role == "map_review" or runtime_role == "plan_review":
            # These reviewed roots are bound through the preregistration itself;
            # the paired executor does not otherwise consume their payloads.
            continue
        expected = {
            "path": roots[f"{runtime_role}_artifact"],
            "root_sha256": roots[f"{runtime_role}_root_sha256"],
        }
        if bound[prereg_role] != expected:
            raise ValueError(f"paired calibration preregistered {prereg_role} drifted")


def _git_head(root: Path) -> str:
    import subprocess

    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "plan",
        "map",
        "route",
        "route-review",
        "runtime",
        "runtime-review",
        "paired-plan",
        "paired-plan-review",
        "preregistration",
        "preregistration-review",
        "training",
        "training-review",
    ):
        parser.add_argument(f"--{name}-artifact", type=Path, required=True)
        parser.add_argument(f"--{name}-root-sha256", required=True)
    parser.add_argument("--probe-template", type=Path, required=True)
    parser.add_argument("--probe-template-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    root = run(**vars(args))
    print(json.dumps({"status": "sealed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
