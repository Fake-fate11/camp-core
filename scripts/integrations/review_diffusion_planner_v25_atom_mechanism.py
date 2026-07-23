#!/usr/bin/env python3
"""Independently reconstruct a sealed V25 atom-mechanism pre-open artifact."""

from __future__ import annotations

import argparse
import json
import math
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
from camp_core.integrations.diffusion_planner_v25_atom_mechanism import (  # noqa: E402
    MECHANISM_SUMMARY_STORAGE_UPPER_BOUND_BYTES,
    analyze_atom_mechanisms,
    validate_atom_mechanism_contract,
)
from camp_core.integrations.diffusion_planner_v25_calibration_analysis import (  # noqa: E402
    _project_complete,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    load_v25_runtime_selector_assets,
)
from scripts.integrations.run_diffusion_planner_v25_candidate0_calibration import (  # noqa: E402
    _canonical_json,
    _sha256,
    _write_json,
)


SCHEMA_VERSION = "camp_dp_v25_atom_mechanism_review_v1"
PRODUCER_SCHEMA_VERSION = "camp_dp_v25_atom_mechanism_artifact_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def review(*, artifact: Path, root_sha256: str, output_dir: Path) -> str:
    source = artifact.resolve()
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    source_seal = verify_complete_seal(source, root_sha256, label="atom-mechanism authority")
    if (source / "run.exit").read_bytes() != b"0\n":
        raise ValueError("atom-mechanism producer did not exit successfully")
    report = _canonical_json(source / "report.json")
    _validate_report(report, source)
    bindings = {
        name: Path(report[f"{name}_artifact"])
        for name in (
            "calibration",
            "recovery",
            "recovery_review",
            "training",
            "training_review",
            "storage_qualification",
            "storage_review",
        )
    }
    for name, path in bindings.items():
        verify_complete_seal(path, report[f"{name}_root_sha256"], label=f"atom-mechanism review {name}")
    if (bindings["calibration"] / "run.exit").read_bytes() != b"1\n":
        raise ValueError("atom-mechanism failed-source terminal state drifted")
    if any((bindings[name] / "run.exit").read_bytes() != b"0\n" for name in ("recovery", "recovery_review", "training", "training_review", "storage_qualification", "storage_review")):
        raise ValueError("atom-mechanism accepted-source terminal state drifted")
    contract_path = Path(report["contract_path"])
    if _sha256(contract_path) != report["contract_sha256"]:
        raise ValueError("atom-mechanism contract source SHA drifted")
    contract = validate_atom_mechanism_contract(_canonical_json(contract_path))
    if not _strict_equal(_canonical_json(source / "mechanism_contract.json"), contract):
        raise ValueError("atom-mechanism frozen contract drifted")
    corpus = _canonical_json(bindings["calibration"] / "paired_calibration_corpus.json")
    if corpus.get("terminal_arm_run_count") != 300 or corpus.get("complete_arm_run_count") != 300 or corpus.get("paired_eligible_pair_count") != 100:
        raise ValueError("atom-mechanism review denominator drifted")
    assets = load_v25_runtime_selector_assets(
        training_artifact=bindings["training"],
        training_root_sha256=report["training_root_sha256"],
        training_review_artifact=bindings["training_review"],
        training_review_root_sha256=report["training_review_root_sha256"],
    )
    runs, references = _review_runs(bindings["calibration"], corpus)
    outcomes = _review_outcomes(corpus)
    independent = analyze_atom_mechanisms(
        decision_runs=runs,
        outcomes_by_unit=outcomes,
        atom_scales=assets.atom_scales,
        static14d_weights=assets.static14d_weights,
        scene14d_provider=assets.scene14d_weight_provider,
        training_artifact=bindings["training"],
    )
    if not _strict_equal(_canonical_json(source / "calibration_atom_mechanism.json"), _json_native(independent)):
        raise ValueError("atom-mechanism analysis differs from independent reconstruction")
    if not _strict_equal(_canonical_json(source / "evidence_references.json"), references):
        raise ValueError("atom-mechanism evidence references drifted")
    storage = _canonical_json(bindings["storage_qualification"] / "report.json")
    storage_review = _canonical_json(bindings["storage_review"] / "report.json")
    expected_with_mechanism = storage["projected_1500_arm_upper_bound_nbytes"] + MECHANISM_SUMMARY_STORAGE_UPPER_BOUND_BYTES
    if (
        report["storage_projected_1500_arm_upper_bound_nbytes_with_mechanism"] != expected_with_mechanism
        or report["fresh_storage_capacity_gate_passed"] is not True
        or storage.get("status") != "passed_fresh_storage_equivalence_and_capacity"
        or storage.get("capacity_gate_passed") is not True
        or storage_review.get("status")
        != "passed_independent_fresh_storage_equivalence_and_capacity_review"
        or storage_review.get("reviewed_root_sha256")
        != report["storage_qualification_root_sha256"]
        or storage_review.get("capacity_gate_passed") is not True
    ):
        raise ValueError("atom-mechanism storage capacity binding drifted")
    output.mkdir(parents=True)
    review_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_atom_mechanism_preopen_review",
        "camp_head": _git_head(ROOT),
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(source),
        "reviewed_root_sha256": source_seal["root_sha256"],
        "paired_unit_count": 100,
        "camp_run_count": len(runs),
        "decision_tick_count": len(runs) * 64,
        "contract_independently_validated": True,
        "same_saved_fixed_k8_pool_reopened": True,
        "scores_margins_ties_and_selected_flips_recomputed": True,
        "corridor_associations_recomputed": True,
        "raw_k8_payload_copied": False,
        "single_atom_closed_loop_causal_effect_claimed": False,
        "primary_fresh_design_changed": False,
        "fresh_storage_capacity_gate_passed": True,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    _write_json(output / "report.json", review_report)
    (output / "HEADS").write_text(
        f"camp_head={review_report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (output / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output / "run.exit").write_text("0\n", encoding="ascii")
    return seal_artifact(output, label="V25 Fresh B2 atom-mechanism independent review")


def _validate_report(value: Mapping[str, Any], source: Path) -> None:
    required = {
        "schema_version": PRODUCER_SCHEMA_VERSION,
        "status": "frozen_atom_mechanism_ready_before_fresh_b2_opening",
        "fixed_dp_head": FIXED_DP_HEAD,
        "calibration_run_exit": 1,
        "paired_unit_count": 100,
        "camp_run_count": 200,
        "decision_tick_count": 12_800,
        "raw_k8_payload_copied": False,
        "same_saved_fixed_k8_pool_used": True,
        "primary_fresh_design_changed": False,
        "model_or_weight_changed": False,
        "single_atom_closed_loop_causal_effect_claimed": False,
        "fresh_storage_capacity_gate_passed": True,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
        "independent_review_completed": False,
    }
    for name, expected in required.items():
        if type(value.get(name)) is not type(expected) or value.get(name) != expected:
            raise ValueError(f"atom-mechanism report field {name} drifted")
    for filename, field in (
        ("mechanism_contract.json", "mechanism_contract_sha256"),
        ("calibration_atom_mechanism.json", "calibration_atom_mechanism_sha256"),
        ("evidence_references.json", "evidence_references_sha256"),
    ):
        if _sha256(source / filename) != value.get(field):
            raise ValueError(f"atom-mechanism report {field} drifted")


def _review_runs(calibration: Path, corpus: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    result = []
    references = []
    for row in corpus["arm_results"]:
        if row["status"] != "complete" or row["plan_arm"] == "candidate0_operational_default":
            continue
        relative = (
            f"runs/{row['run_ordinal']:04d}_{row['unit_ordinal']:04d}_"
            f"{row['arm_order_index']}_{row['plan_arm']}/decision_evidence.json"
        )
        evidence_path = calibration / relative
        evidence = _strict_sealed_external_json_array(evidence_path)
        evidence_sha = _sha256(evidence_path)
        native = row["native_receipt"]
        if type(evidence) is not list or len(evidence) != 64 or native.get("calibration_decision_evidence_sha256") != evidence_sha or native.get("calibration_decision_evidence_count") != 64:
            raise ValueError("atom-mechanism reviewer decision evidence drifted")
        result.append({
            "plan_arm": row["plan_arm"],
            "unit_ordinal": row["unit_ordinal"],
            "corridor_sha256": row["corridor_sha256"],
            "snapshots": evidence,
            "native_ticks": native["ticks"],
            "scenario_family": row["scenario_family"],
            "risk_tier": row["risk_tier"],
            "signal_source_class": row["signal_source_class"],
            "phase_authority_mode": row["phase_authority_mode"],
        })
        references.append({
            "unit_ordinal": row["unit_ordinal"],
            "plan_arm": row["plan_arm"],
            "relative_path": relative,
            "logical_sha256": evidence_sha,
            "logical_bytes": evidence_path.stat().st_size,
            "raw_payload_copied": False,
        })
    return result, references


def _strict_sealed_external_json_array(path: Path) -> list[Any]:
    """Independently open immutable accepted raw evidence with strict JSON semantics."""
    value = json.loads(
        path.read_bytes().decode("utf-8", "strict"),
        object_pairs_hook=_no_duplicate_pairs,
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )
    if type(value) is not list:
        raise ValueError(f"sealed external JSON array expected: {path}")
    _require_finite_json(value, path=path)
    return value


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _require_finite_json(value: Any, *, path: Path) -> None:
    if type(value) is float and not math.isfinite(value):
        raise ValueError(f"nonfinite sealed external JSON value: {path}")
    if type(value) is list:
        for item in value:
            _require_finite_json(item, path=path)
    elif type(value) is dict:
        for item in value.values():
            _require_finite_json(item, path=path)


def _review_outcomes(corpus: Mapping[str, Any]) -> dict[int, dict[str, Mapping[str, Any]]]:
    result: dict[int, dict[str, Mapping[str, Any]]] = {}
    for row in corpus["arm_results"]:
        if row["status"] != "complete":
            raise ValueError("atom-mechanism review requires complete calibration pairs")
        result.setdefault(row["unit_ordinal"], {})[row["plan_arm"]] = _project_complete(row)
    return result


def _json_native(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False))


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(_strict_equal(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(_strict_equal(a, b) for a, b in zip(left, right, strict=True))
    return bool(left == right)


def _git_head(path: Path) -> str:
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = review(**vars(args))
    print(json.dumps({"status": "sealed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
