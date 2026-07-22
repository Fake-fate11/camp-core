#!/usr/bin/env python3
"""Independently review recovered analysis over immutable calibration evidence."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
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
from camp_core.integrations.diffusion_planner_v25_calibration_analysis import (  # noqa: E402
    analyze_paired_calibration_outcomes,
)
from camp_core.integrations.diffusion_planner_v25_calibration_atoms import (  # noqa: E402
    analyze_calibration_decision_evidence,
)
from camp_core.integrations.diffusion_planner_v25_calibration_preregistration import (  # noqa: E402
    validate_paired_calibration_preregistration,
)
from camp_core.integrations.diffusion_planner_v25_paired_calibration import (  # noqa: E402
    validate_paired_calibration_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    load_v25_runtime_selector_assets,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_execution import (  # noqa: E402
    build_paired_calibration_arm_config,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (  # noqa: E402
    validate_signal_complete_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_runtime import (  # noqa: E402
    build_signal_complete_runtime_case,
)
from scripts.integrations import (  # noqa: E402
    review_diffusion_planner_v25_paired_calibration as rev,
)
from scripts.integrations.recover_diffusion_planner_v25_paired_calibration_analysis import (  # noqa: E402
    EXPECTED_FAILURE,
    FAILED_EXECUTION_ROOT,
    SCHEMA_VERSION as RECOVERY_SCHEMA_VERSION,
)


SCHEMA_VERSION = "camp_dp_v25_paired_calibration_recovery_review_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
ORIGINAL_CAMP_HEAD = "325cd486fa0992a83927b1270093a4d6187efaf7"


def review_recovery(
    *,
    recovery_artifact: Path,
    recovery_root_sha256: str,
    failed_artifact: Path,
    failed_root_sha256: str,
    localization_receipt: Path,
    localization_receipt_sha256: str,
    dp_repo: Path,
    output_dir: Path,
) -> str:
    recovery = recovery_artifact.resolve()
    failed = failed_artifact.resolve()
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    recovery_seal = verify_complete_seal(
        recovery, recovery_root_sha256, label="paired calibration recovery analysis"
    )
    if (recovery / "run.exit").read_bytes() != b"0\n":
        raise ValueError("recovery analysis did not exit successfully")
    failed_seal = verify_complete_seal(
        failed, failed_root_sha256, label="failed paired calibration raw evidence"
    )
    if failed_root_sha256 != FAILED_EXECUTION_ROOT:
        raise ValueError("unexpected failed calibration root")
    if (failed / "run.exit").read_bytes() != b"1\n":
        raise ValueError("original calibration failure exit drifted")
    if rev._canonical_json(failed / "failure.json") != EXPECTED_FAILURE:
        raise ValueError("original calibration failure receipt drifted")
    _validate_original_heads(failed / "HEADS")

    dp_root = dp_repo.resolve()
    if rev._git_head(dp_root) != FIXED_DP_HEAD or rev._tracked_dirty(dp_root):
        raise ValueError("fixed DP HEAD drifted or tracked worktree is dirty")
    receipt_path = localization_receipt.resolve()
    if rev._sha256(receipt_path) != localization_receipt_sha256:
        raise ValueError("localization receipt SHA drifted")
    localization = rev._canonical_json(receipt_path)
    if (
        localization.get("classification")
        != "A_terminal_analyzer_latency_registry_harness_defect"
        or localization.get("execution_root_sha256") != failed_root_sha256
        or localization.get("native_tick_count") != 19_200
        or localization.get("fresh_b2_opened") is not False
        or localization.get("fresh_outcome_fields_consumed") != []
    ):
        raise ValueError("localization receipt authority drifted")

    report = rev._canonical_json(recovery / "report.json")
    _validate_recovery_report(
        report,
        recovery=recovery,
        failed=failed,
        failed_root_sha256=failed_root_sha256,
        localization_receipt=receipt_path,
        localization_receipt_sha256=localization_receipt_sha256,
    )
    roots = report["input_roots"]
    rev._verify_input_roots(roots)
    base = validate_signal_complete_execution_plan(
        rev._canonical_json(Path(roots["plan_artifact"]) / "execution_plan.json")
    )
    paired = validate_paired_calibration_execution_plan(
        rev._canonical_json(
            Path(roots["paired_plan_artifact"]) / "paired_calibration_plan.json"
        ),
        calibration_plan=base,
    )
    preregistration = validate_paired_calibration_preregistration(
        rev._canonical_json(
            Path(roots["preregistration_artifact"]) / "preregistration.json"
        )
    )
    rev._verify_preregistered_root_chain(preregistration, roots)
    probe = rev._legacy_json_object(
        Path(report["probe_template"]), report["probe_template_sha256"]
    )
    route_rows = rev._canonical_json(
        Path(roots["route_artifact"]) / "route_assets.json"
    )["route_assets"]
    route_by_identity = {
        row["route_identity_sha256"]: dict(row["route_asset"])
        for row in route_rows
    }
    identities = {
        row["scenario_identity_sha256"]: row for row in paired["identities"]
    }
    prepared = {
        identity["scenario_identity_sha256"]: build_signal_complete_runtime_case(
            identity,
            map_artifact=Path(roots["map_artifact"]),
            seeds=base["seeds"],
        )
        for identity in base["identities"]
    }
    rev._bind_reviewed_runtime_receipts(
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
    selector = rev._selector_authority(assets, roots)
    rev._verify_model_preregistration(preregistration, selector, assets)

    results = rev._canonical_json_list(failed / "run_results.json")
    run_dirs = sorted((failed / "runs").iterdir())
    if len(results) != 300 or len(run_dirs) != 300:
        raise ValueError("raw calibration denominator drifted")
    camp_runs: list[dict[str, Any]] = []
    pairs: dict[int, dict[str, Mapping[str, Any]]] = defaultdict(dict)
    ordinal = 0
    latency_count = 0
    for unit in paired["execution_units"]:
        identity = identities[unit["scenario_identity_sha256"]]
        route_asset = route_by_identity[identity["route_identity_sha256"]]
        for arm_order_index, plan_arm in enumerate(unit["ordered_arms"]):
            result = results[ordinal]
            run_dir = run_dirs[ordinal]
            expected_name = (
                f"{ordinal:04d}_{unit['unit_ordinal']:04d}_"
                f"{arm_order_index}_{plan_arm}"
            )
            if run_dir.name != expected_name:
                raise ValueError("raw calibration run order drifted")
            expected_config = build_paired_calibration_arm_config(
                probe_template=probe,
                prepared_runtime=prepared[unit["scenario_identity_sha256"]],
                execution_unit=unit,
                plan_arm=plan_arm,
                route_asset=route_asset,
                dp_repo=dp_root,
                runtime_selector_authority=selector,
            )
            if not rev._strict_equal(
                rev._canonical_json(run_dir / "run_config.json"), expected_config
            ):
                raise ValueError("raw calibration run config drifted")
            if not rev._strict_equal(
                rev._canonical_json(run_dir / "terminal.json"), result
            ):
                raise ValueError("raw calibration terminal binding drifted")
            rev._review_terminal_metadata(
                result,
                ordinal=ordinal,
                unit=unit,
                identity=identity,
                arm_order_index=arm_order_index,
                plan_arm=plan_arm,
            )
            if result["status"] != "complete":
                raise ValueError("recovery requires all 300 raw runs complete")
            decision = rev._review_complete(
                execution=failed,
                run_dir=run_dir,
                result=result,
                unit=unit,
                identity=identity,
                route_asset=route_asset,
                plan_arm=plan_arm,
            )
            if decision is not None:
                camp_runs.append(decision)
            for tick in result["native_receipt"]["ticks"]:
                value = tick["latency_ms"]["input_materialization"]
                if type(value) is not float or not math.isfinite(value) or value < 0.0:
                    raise ValueError("input-materialization latency drifted")
                latency_count += 1
            pairs[unit["unit_ordinal"]][plan_arm] = result
            ordinal += 1
    rev._review_initial_pairing(pairs)
    reconstructed = rev._independent_corpus(paired, results)
    recorded = rev._canonical_json(failed / "paired_calibration_corpus.json")
    if not rev._strict_equal(recorded, reconstructed):
        raise ValueError("raw calibration corpus differs from reconstruction")
    independent_analysis = analyze_paired_calibration_outcomes(reconstructed)
    if not rev._strict_equal(
        rev._canonical_json(recovery / "calibration_analysis.json"),
        _canonical_json_native(independent_analysis),
    ):
        raise ValueError("recovery analysis differs from independent reconstruction")
    independent_atoms = analyze_calibration_decision_evidence(
        camp_runs=camp_runs,
        atom_scales=assets.atom_scales,
        static14d_weights=assets.static14d_weights,
        scene14d_provider=assets.scene14d_weight_provider,
        training_artifact=Path(roots["training_artifact"]),
    )
    if not rev._strict_equal(
        rev._canonical_json(recovery / "atom_calibration.json"),
        _canonical_json_native(independent_atoms),
    ):
        raise ValueError("recovery atom evidence differs from reconstruction")
    if latency_count != 19_200:
        raise ValueError("supplementary latency denominator drifted")

    output.mkdir(parents=True)
    review_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_paired_calibration_recovery_review",
        "camp_head": rev._git_head(ROOT),
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_recovery_artifact": str(recovery),
        "reviewed_recovery_root_sha256": recovery_seal["root_sha256"],
        "original_execution_artifact": str(failed),
        "original_execution_root_sha256": failed_seal["root_sha256"],
        "original_execution_run_exit": 1,
        "original_raw_evidence_modified": False,
        "terminal_arm_run_count": 300,
        "complete_arm_run_count": 300,
        "paired_eligible_pair_count": 100,
        "native_tick_count": 19_200,
        "input_materialization_latency_count": latency_count,
        "input_materialization_classification": "supplementary_runtime_latency",
        "all_configs_independently_rebuilt": True,
        "all_terminal_rows_reconstructed": True,
        "all_complete_receipts_revalidated": True,
        "all_initial_pair_resets_rechecked": True,
        "calibration_analysis_rederived": True,
        "atom_scores_and_selections_rederived": True,
        "model_or_threshold_change_executed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
        "claim_authorized": False,
    }
    rev._write_json(output / "report.json", review_report)
    (output / "HEADS").write_text(
        f"camp_head={review_report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (output / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output / "run.exit").write_text("0\n", encoding="ascii")
    return seal_artifact(output, label="V25 paired calibration recovery review")


def _validate_original_heads(path: Path) -> None:
    rows = {}
    for line in path.read_text(encoding="ascii").splitlines():
        key, value = line.split("=", 1)
        rows[key] = value
    if rows != {"camp_head": ORIGINAL_CAMP_HEAD, "fixed_dp_head": FIXED_DP_HEAD}:
        raise ValueError("original calibration HEADS drifted")


def _canonical_json_native(value: Any) -> Any:
    """Apply the frozen JSON value contract before exact reviewer comparison."""
    return json.loads(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    )


def _validate_recovery_report(
    value: Mapping[str, Any],
    *,
    recovery: Path,
    failed: Path,
    failed_root_sha256: str,
    localization_receipt: Path,
    localization_receipt_sha256: str,
) -> None:
    required = {
        "schema_version": RECOVERY_SCHEMA_VERSION,
        "status": "recovered_calibration_analysis_complete_fresh_closed",
        "fixed_dp_head": FIXED_DP_HEAD,
        "original_execution_artifact": str(failed),
        "original_execution_root_sha256": failed_root_sha256,
        "original_execution_run_exit": 1,
        "original_terminal_analysis_failure": EXPECTED_FAILURE["reason"],
        "original_raw_evidence_modified": False,
        "localization_receipt": str(localization_receipt),
        "localization_receipt_sha256": localization_receipt_sha256,
        "terminal_arm_run_count": 300,
        "complete_arm_run_count": 300,
        "paired_eligible_pair_count": 100,
        "native_tick_count": 19_200,
        "input_materialization_latency_count": 19_200,
        "input_materialization_classification": "supplementary_runtime_latency",
        "model_or_threshold_changed": False,
        "raw_outcome_or_selection_changed": False,
        "independent_review_completed": False,
        "accepted_as_fresh_or_claim_evidence": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    for name, expected in required.items():
        if type(value.get(name)) is not type(expected) or value.get(name) != expected:
            raise ValueError(f"recovery report field {name} drifted")
    if (
        value.get("calibration_analysis_sha256")
        != rev._sha256(recovery / "calibration_analysis.json")
        or value.get("atom_calibration_sha256")
        != rev._sha256(recovery / "atom_calibration.json")
    ):
        raise ValueError("recovery report payload SHA drifted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recovery-artifact", type=Path, required=True)
    parser.add_argument("--recovery-root-sha256", required=True)
    parser.add_argument("--failed-artifact", type=Path, required=True)
    parser.add_argument("--failed-root-sha256", required=True)
    parser.add_argument("--localization-receipt", type=Path, required=True)
    parser.add_argument("--localization-receipt-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = review_recovery(**vars(args))
    print(json.dumps({"status": "sealed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
