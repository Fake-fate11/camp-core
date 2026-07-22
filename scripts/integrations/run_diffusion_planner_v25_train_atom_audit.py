#!/usr/bin/env python3
"""Build the sealed train-only V25 atom audit and fair training projection."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_train_atom_audit import (  # noqa: E402
    ATOM_COUNT,
    DEFAULT_LABEL_SEVERITY,
    build_train_only_causal_labels,
    compute_train_atom_audit,
    fit_train_only_atom_scales,
)
from camp_core.integrations.diffusion_planner_v25_train_corpus import (  # noqa: E402
    FIXED_DP_HEAD,
    load_reviewed_train_corpus,
)


SCHEMA_VERSION = "camp_dp_v25_train_only_atom_audit_artifact_v1"
TRAINING_ROWS_SCHEMA_VERSION = "camp_dp_v25_fair_2x2_training_rows_v1"
FROZEN_TRAINING_CONFIG = (
    ROOT / "configs" / "integrations" / "diffusion_planner_v25_training_v1.json"
)
FROZEN_TRAINING_CONFIG_SHA256 = (
    "939a4cf4275daa205cad0aaf5aef25cfb65e5f9cc412e389191cae14d5044422"
)


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def _tracked_dirty() -> bool:
    return bool(
        subprocess.check_output(
            ["git", "-C", str(ROOT), "status", "--short", "--untracked-files=no"],
            text=True,
        ).strip()
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.write_bytes(
        (
            json.dumps(
                payload,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    )


def _read_generation_scales(path: Path) -> np.ndarray:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if type(payload) is not dict:
        raise ValueError("generation scale file must be a JSON object")
    raw = np.asarray(payload.get("scales"))
    if (
        payload.get("atom_schema_version") != "dp_camp_v10_14d"
        or raw.shape != (ATOM_COUNT,)
        or raw.dtype.kind not in "fiu"
        or raw.dtype.kind == "b"
    ):
        raise ValueError("generation scale schema drifted")
    scales = raw.astype(np.float64, copy=False)
    if not np.all(np.isfinite(scales)) or np.any(scales <= 0.0):
        raise ValueError("generation scales must be finite strictly positive")
    return scales


def _audit_contract() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if _sha256(FROZEN_TRAINING_CONFIG) != FROZEN_TRAINING_CONFIG_SHA256:
        raise ValueError("V25 training/audit config SHA drifted")
    payload = json.loads(FROZEN_TRAINING_CONFIG.read_text(encoding="utf-8"))
    audit = payload.get("train_only_atom_audit_contract")
    if type(audit) is not dict or set(audit) != {
        "scale_estimator",
        "scale_quantile",
        "minimum_positive_candidate_rows",
        "minimum_positive_semantic_blocks",
        "zero_support_policy",
        "support_limited_red_policy",
        "causal_policy_distillation",
    }:
        raise ValueError("train-only atom audit config field set drifted")
    labels = audit.get("causal_policy_distillation")
    if (
        audit.get("scale_estimator")
        != "positive_support_block_weighted_inverse_empirical_q95"
        or audit.get("scale_quantile") != 0.95
        or audit.get("minimum_positive_candidate_rows") != 128
        or audit.get("minimum_positive_semantic_blocks") != 20
        or audit.get("zero_support_policy")
        != "keep_14d_dimension_masked_and_use_neutral_unit_scale_not_generation_floor"
        or audit.get("support_limited_red_policy")
        != "binary_scale_1_not_degenerate_continuous_floor"
        or type(labels) is not dict
        or set(labels)
        != {
            "severity_14d",
            "physical_penalty",
            "margin_multiplier",
            "margin_clip",
            "eligibility",
            "tie_break",
            "closed_loop_outcome_consumed",
            "fresh_b2_consumed",
            "identity_fields_used_as_label_or_feature",
        }
        or labels.get("severity_14d") != DEFAULT_LABEL_SEVERITY.tolist()
        or labels.get("physical_penalty") != 100.0
        or labels.get("margin_multiplier") != 0.1
        or labels.get("margin_clip") != 2.0
        or labels.get("eligibility") != "source_valid_candidate_set"
        or labels.get("tie_break") != "lowest_candidate_index"
        or labels.get("closed_loop_outcome_consumed") is not False
        or labels.get("fresh_b2_consumed") is not False
        or labels.get("identity_fields_used_as_label_or_feature") is not False
    ):
        raise ValueError("train-only atom audit config value contract drifted")
    return payload, audit, labels


def build(
    *,
    corpus_artifact: Path,
    corpus_root_sha256: str,
    corpus_review_artifact: Path,
    corpus_review_root_sha256: str,
    generation_scales_path: Path,
    output_dir: Path,
) -> str:
    if _tracked_dirty():
        raise ValueError("CAMP tracked worktree must be clean")
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    try:
        training_config, audit_contract, label_contract = _audit_contract()
        corpus = load_reviewed_train_corpus(
            corpus_artifact,
            corpus_root_sha256,
            corpus_review_artifact,
            corpus_review_root_sha256,
        )
        generation_sha = _sha256(generation_scales_path)
        if generation_sha != corpus.generation_behavior_scale_sha256:
            raise ValueError("generation scale asset differs from sealed corpus")
        generation_scales = _read_generation_scales(generation_scales_path)
        scale_report = fit_train_only_atom_scales(
            corpus.raw_atoms,
            corpus.source_valid_mask,
            corpus.atom_source_valid_mask,
            corpus.atom_applicable_mask,
            corpus.snapshot_weights,
            corpus.semantic_block_ids,
            quantile=float(audit_contract["scale_quantile"]),
            minimum_positive_rows=int(
                audit_contract["minimum_positive_candidate_rows"]
            ),
            minimum_positive_blocks=int(
                audit_contract["minimum_positive_semantic_blocks"]
            ),
        )
        training_scales = np.asarray(scale_report["scales"], dtype=np.float64)
        labels = build_train_only_causal_labels(
            corpus.raw_atoms,
            corpus.source_valid_mask,
            corpus.atom_source_valid_mask,
            corpus.atom_applicable_mask,
            corpus.physical_feasible_mask,
            training_scales,
            severity=np.asarray(label_contract["severity_14d"], dtype=np.float64),
            physical_penalty=float(label_contract["physical_penalty"]),
            margin_multiplier=float(label_contract["margin_multiplier"]),
            margin_clip=float(label_contract["margin_clip"]),
        )
        audit = compute_train_atom_audit(
            corpus.raw_atoms,
            corpus.source_valid_mask,
            corpus.atom_source_valid_mask,
            corpus.atom_applicable_mask,
            corpus.physical_feasible_mask,
            corpus.snapshot_weights,
            corpus.semantic_block_ids,
            corpus.route_ids,
            corpus.family_tier,
            training_scales,
            severity=np.asarray(label_contract["severity_14d"], dtype=np.float64),
            generation_scales=generation_scales,
            minimum_positive_rows=int(
                audit_contract["minimum_positive_candidate_rows"]
            ),
            minimum_positive_blocks=int(
                audit_contract["minimum_positive_semantic_blocks"]
            ),
        )
        np.savez_compressed(
            output_dir / "training_rows.npz",
            schema_version=np.asarray(TRAINING_ROWS_SCHEMA_VERSION),
            normalized_atoms_14d=labels["normalized_atoms"].astype(np.float64),
            raw_atoms=corpus.raw_atoms,
            oracle_indices=labels["oracle_indices"].astype(np.int64),
            margins=labels["margins"].astype(np.float64),
            source_valid_mask=corpus.source_valid_mask,
            atom_source_valid_mask=corpus.atom_source_valid_mask,
            atom_applicable_mask=corpus.atom_applicable_mask,
            physical_feasible_mask=corpus.physical_feasible_mask,
            raw_context=corpus.raw_context,
            context_source_complete=corpus.context_source_complete,
            record_weights=corpus.snapshot_weights,
            route_ids=np.asarray(corpus.route_ids),
            semantic_block_ids=np.asarray(corpus.semantic_block_ids),
            corridor_ids=np.asarray(corpus.corridor_ids),
            map_family_ids=np.asarray(corpus.map_family_ids),
            family_tier=np.asarray(corpus.family_tier),
            seeds=np.asarray(corpus.seeds, dtype=np.int64),
            ticks=np.asarray(corpus.ticks, dtype=np.int64),
            scenario_ids=np.asarray(corpus.scenario_ids),
            training_scales=training_scales,
            severity=DEFAULT_LABEL_SEVERITY,
        )
        rows_sha = _sha256(output_dir / "training_rows.npz")
        label_report = {
            "schema_version": "camp_dp_v25_train_only_causal_label_sidecar_v1",
            "label_contract": "causal_policy_distillation_no_outcome",
            "physical_penalty": label_contract["physical_penalty"],
            "margin_multiplier": label_contract["margin_multiplier"],
            "margin_clip": label_contract["margin_clip"],
            "severity": list(label_contract["severity_14d"]),
            "oracle_index_sha256": hashlib.sha256(
                np.ascontiguousarray(labels["oracle_indices"]).tobytes()
            ).hexdigest(),
            "margin_sha256": hashlib.sha256(
                np.ascontiguousarray(labels["margins"]).tobytes()
            ).hexdigest(),
            "identity_fields_used_as_label_or_feature": False,
            "fresh_or_outcome_consumed": False,
        }
        serialized_scale_report = dict(scale_report)
        serialized_scale_report["scales"] = training_scales.tolist()
        _write_json(output_dir / "training_scales.json", serialized_scale_report)
        _write_json(output_dir / "atom_audit.json", audit)
        _write_json(output_dir / "label_sidecar.json", label_report)
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": "passed_train_only_atom_audit_projection",
            "camp_head": _git_head(),
            "fixed_dp_head": FIXED_DP_HEAD,
            "corpus": corpus.report,
            "generation_scales_path": str(generation_scales_path.resolve()),
            "generation_scales_sha256": generation_sha,
            "training_config": str(FROZEN_TRAINING_CONFIG.resolve()),
            "training_config_sha256": FROZEN_TRAINING_CONFIG_SHA256,
            "training_config_payload": training_config,
            "train_only_atom_audit_contract": audit_contract,
            "training_rows_schema_version": TRAINING_ROWS_SCHEMA_VERSION,
            "training_rows_sha256": rows_sha,
            "snapshot_count": int(corpus.raw_atoms.shape[0]),
            "candidate_count": int(corpus.raw_atoms.shape[0] * 8),
            "atom_count": ATOM_COUNT,
            "training_scale_status_counts": {
                status: sum(
                    row["status"] == status for row in scale_report["atom_rows"]
                )
                for status in ("PASS", "WARN", "FAIL")
            },
            "atom_audit_status_counts": audit["status_counts"],
            "atom_audit_status_scope": audit["status_scope"],
            "static_correctness_prerequisite": audit[
                "static_correctness_prerequisite"
            ],
            "models_authorized_by_projection": [
                "CAMP-Static14D",
                "CAMP-Scene14D",
                "CAMP-Static9D",
                "CAMP-Scene9D",
            ],
            "primary_methods": ["CAMP-Static14D", "CAMP-Scene14D"],
            "paper_subset_ablations": ["CAMP-Static9D", "CAMP-Scene9D"],
            "training_executed": False,
            "calibration_executed": False,
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
        }
        _write_json(output_dir / "report.json", report)
        (output_dir / "HEADS").write_text(
            f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (output_dir / "COMMAND").write_text(
            " ".join(sys.argv) + "\n", encoding="utf-8"
        )
        (output_dir / "run.exit").write_text("0\n", encoding="ascii")
        return seal_artifact(output_dir, label="V25 train-only atom audit")
    except BaseException as exc:
        _write_json(
            output_dir / "failure.json",
            {"schema_version": SCHEMA_VERSION, "status": "failed", "reason": str(exc)},
        )
        (output_dir / "run.exit").write_text("1\n", encoding="ascii")
        seal_artifact(output_dir, label="failed V25 train-only atom audit")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-artifact", type=Path, required=True)
    parser.add_argument("--corpus-root-sha256", required=True)
    parser.add_argument("--corpus-review-artifact", type=Path, required=True)
    parser.add_argument("--corpus-review-root-sha256", required=True)
    parser.add_argument("--generation-scales-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = build(**vars(args))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
