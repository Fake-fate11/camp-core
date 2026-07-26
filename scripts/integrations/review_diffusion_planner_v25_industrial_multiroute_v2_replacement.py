from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camp_core", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2_replacement_review import (  # noqa: E402
    EXPECTED_AUTHORITY,
    EXPECTED_FIXED_DP,
    EXPECTED_OLD_CLASSIFICATION,
    EXPECTED_SELECTED_MANIFEST,
    literal_exact_dirs,
    literal_semantic_receipt,
    review_contract_semantics,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
)


OLD_CONTROL = Path(
    "/root/autodl-tmp/"
    ".camp_dp_v25_industrial_v3_multiroute_v2_9bef998d_89e716d0_"
    "execution_control"
)
OLD_LAUNCHER = Path(
    "/root/autodl-tmp/"
    ".camp_dp_v25_industrial_v3_multiroute_v2_9bef998d_89e716d0_"
    "execution_launcher"
)
EXPECTED_STDOUT = (
    "09d098f6e83a40b60fdab9d9eac49c1f991ea75e73e736a842b78ab5bcbed68c"
)
EXPECTED_STDERR = (
    "c6ad03d83a3a58bd6b7505bbd8338e58b3024d4575d412a850e203b1d516b7ae"
)
EXPECTED_SOURCE_ROOT = (
    "ebbc7140e65fb2d2baf2aed8fa1a990e3c47b8b8ed3f6f4583ae0e2121be065a"
)
EXPECTED_SOURCE_REVIEW_ROOT = (
    "15f574596d21eaeec272ec181b744d3b508db02f431325cb198f26217927e9a3"
)


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify(path: Path, root: str, label: str) -> dict[str, Any]:
    verify_complete_seal(path, root, label=label)
    return object_from(path / "report.json")


def _write(
    output: Path,
    report: Mapping[str, Any],
    *,
    role: str,
    source_root: str,
    implementation_head: str,
) -> str:
    return write_atomic(
        output,
        dict(report),
        {
            "role": role,
            "authority_sha256": EXPECTED_AUTHORITY,
            "implementation_head": implementation_head,
            "fixed_dp_head": EXPECTED_FIXED_DP,
            "source_root_sha256": source_root,
        },
        label=f"V25 multiroute-v2 replacement {role}",
    )


def review_closeout(output: Path, *, source_dir: Path, source_root: str) -> str:
    source = _verify(source_dir, source_root, "replacement old attempt closeout")
    milestone = object_from(OLD_CONTROL / "milestone.json")
    cluster_dirs = sorted(
        path.name
        for path in (OLD_CONTROL / "clusters").iterdir()
        if path.is_dir()
    )
    if (
        source["classification"] != EXPECTED_OLD_CLASSIFICATION
        or source["milestone"] != milestone
        or milestone
        != {
            "completed_clusters": 5,
            "completed_tick_slots": 960,
            "formal_model_calls": 960,
            "last_cluster_index": 4,
        }
        or cluster_dirs != [f"{index:03d}" for index in range(5)]
        or Path(str(OLD_LAUNCHER) + ".run.exit")
        .read_text(encoding="ascii")
        .strip()
        != "1"
        or _file_sha(Path(str(OLD_LAUNCHER) + ".stdout")) != EXPECTED_STDOUT
        or _file_sha(Path(str(OLD_LAUNCHER) + ".stderr")) != EXPECTED_STDERR
        or source["execution_artifact_formed"] is not False
        or source["old_partial_reuse"] is not False
        or source["cluster_effect_or_outcome_values_read"] is not False
    ):
        raise ValueError("independent old-attempt closeout review failed")
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "old_attempt_closeout_review_v1"
        ),
        "status": "independent_outcome_blind_closeout_review_passed",
        "authority_sha256": EXPECTED_AUTHORITY,
        "source_root_sha256": source_root,
        "classification": EXPECTED_OLD_CLASSIFICATION,
        "completed_clusters": 5,
        "completed_tick_slots": 960,
        "formal_model_calls": 960,
        "old_partial_reuse": False,
        "outcome_values_read": False,
        "producer_failure_or_effect_oracle_imported": False,
    }
    return _write(
        output,
        report,
        role="old_attempt_closeout_review",
        source_root=source_root,
        implementation_head=git_head(),
    )


def review_contract(output: Path, *, source_dir: Path, source_root: str) -> str:
    source = _verify(source_dir, source_root, "replacement contract")
    reviewed = review_contract_semantics(source["contract"])
    preimage = source["continuation_preimage"]
    continuation_sha = hashlib.sha256(
        (
            __import__("json").dumps(
                preimage,
                sort_keys=True,
                ensure_ascii=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("ascii")
    ).hexdigest()
    if (
        source["authority_sha256"] != EXPECTED_AUTHORITY
        or source["fixed_dp_head"] != EXPECTED_FIXED_DP
        or source["replacement_continuation_sha256"] != continuation_sha
        or reviewed["authority"]["replacement_continuation_sha256"]
        != continuation_sha
        or reviewed["exact_dirs"]
        != literal_exact_dirs(source["implementation_head"], continuation_sha)
        or preimage["old_attempt_closeout_root"]
        != reviewed["old_attempt"]["closeout_root"]
        or preimage["old_attempt_closeout_review_root"]
        != reviewed["old_attempt"]["closeout_review_root"]
        or source["model_pool_selector_calls"] != 0
        or source["outcome_values_read"] is not False
    ):
        raise ValueError("independent replacement contract review failed")
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "replacement_contract_review_v1"
        ),
        "status": "independent_literal_contract_and_continuation_review_passed",
        "authority_sha256": EXPECTED_AUTHORITY,
        "source_root_sha256": source_root,
        "contract_sha256": reviewed["contract_sha256"],
        "replacement_continuation_sha256": continuation_sha,
        "local_literal_checks": {
            "source_roots_and_parent_authorities": True,
            "old_partial_closeout_and_no_reuse": True,
            "availability_driven_formal_semantics": True,
            "252x64_zero_model_dryrun": True,
            "100x3x64_start_from_zero": True,
            "161_leaf_no_weighted_total_no_claim": True,
            "exact_dirs": True,
        },
        "producer_contract_adapter_or_decision_oracle_imported": False,
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
    }
    return _write(
        output,
        report,
        role="contract_review",
        source_root=source_root,
        implementation_head=source["implementation_head"],
    )


def review_matrix(
    output: Path,
    *,
    source_dir: Path,
    source_root: str,
    contract_dir: Path,
    contract_root: str,
) -> str:
    source = _verify(source_dir, source_root, "replacement semantic matrix")
    contract = _verify(contract_dir, contract_root, "replacement contract")
    parameters = [row["parameter"] for row in source["rows"]]
    expected = [
        "source_availability",
        "formal_phase",
        "formal_signal_objects",
        "future_phase_schedule",
        "runtime_authority",
        "full_denominator_and_failure",
    ]
    if (
        parameters != expected
        or any(row["implicit_default_allowed"] for row in source["rows"])
        or source["residual_risk_register"]["zero_bug_claimed"] is not False
        or output.resolve()
        != Path(contract["contract"]["exact_dirs"]["semantic_hardening_matrix_review"])
    ):
        raise ValueError("independent semantic matrix review failed")
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "replacement_semantic_hardening_matrix_review_v1"
        ),
        "status": "independent_parameter_propagation_review_passed",
        "authority_sha256": EXPECTED_AUTHORITY,
        "source_root_sha256": source_root,
        "contract_root_sha256": contract_root,
        "exact_parameter_set": expected,
        "family_fallback_or_implicit_default_allowed": False,
        "producer_matrix_or_adapter_oracle_imported": False,
        "model_pool_selector_calls": 0,
    }
    return _write(
        output,
        report,
        role="semantic_hardening_matrix_review",
        source_root=source_root,
        implementation_head=contract["implementation_head"],
    )


def review_dryrun(
    output: Path,
    *,
    source_dir: Path,
    source_root: str,
    contract_dir: Path,
    contract_root: str,
    source_materialization_dir: Path,
    source_materialization_root: str,
) -> str:
    source = _verify(source_dir, source_root, "replacement semantic dry-run")
    contract = _verify(contract_dir, contract_root, "replacement contract")
    _verify(
        source_materialization_dir,
        source_materialization_root,
        "project source materialization",
    )
    if (
        source_materialization_root != EXPECTED_SOURCE_ROOT
        or output.resolve()
        != Path(contract["contract"]["exact_dirs"]["semantic_adapter_dryrun_review"])
    ):
        raise ValueError("dry-run review authority drifted")
    records = object_from(source_materialization_dir / "source_records.json")["records"]
    receipts = object_from(source_dir / "receipts.json")["receipts"]
    if len(records) != 252 or len(receipts) != 16_128:
        raise ValueError("dry-run review denominator drifted")
    mapped = no_signal = 0
    phases = {"green": 0, "yellow": 0, "red": 0}
    position = 0
    for record in records:
        for tick in range(64):
            expected = literal_semantic_receipt(record, tick)
            if receipts[position] != expected:
                raise ValueError(
                    f"dry-run semantic receipt mismatch at ordinal "
                    f"{record['ordinal']} tick {tick}"
                )
            if expected["source_availability"] == "no_signal":
                no_signal += 1
                if (
                    expected["formal_phase"] != "none"
                    or expected["formal_mapped_source_required"] is not False
                    or any(expected["formal_signal_object_counts"].values())
                ):
                    raise ValueError("no-signal formal absence drifted")
            else:
                mapped += 1
                phases[expected["formal_phase"]] += 1
                if (
                    expected["formal_mapped_source_required"] is not True
                    or expected["same_tick_phase_authority"] is not True
                ):
                    raise ValueError("mapped same-tick authority drifted")
            if (
                expected["future_phase_consumed"] is not False
                or expected["future_schedule_consumed"] is not False
            ):
                raise ValueError("future phase leakage detected")
            position += 1
    if (
        mapped != 8064
        or no_signal != 8064
        or any(phases[value] == 0 for value in phases)
    ):
        raise ValueError("dry-run review semantic coverage drifted")
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "replacement_semantic_adapter_dryrun_review_v1"
        ),
        "status": "independent_16128_receipt_semantic_review_passed",
        "authority_sha256": EXPECTED_AUTHORITY,
        "source_root_sha256": source_root,
        "contract_root_sha256": contract_root,
        "receipt_count": 16_128,
        "mapped_signal_receipts": mapped,
        "no_signal_receipts": no_signal,
        "mapped_phase_receipt_counts": phases,
        "future_phase_or_schedule_consumed_count": 0,
        "producer_adapter_decision_oracle_imported": False,
        "model_pool_selector_calls": 0,
        "outcome_values_read": False,
    }
    return _write(
        output,
        report,
        role="semantic_adapter_dryrun_review",
        source_root=source_root,
        implementation_head=contract["implementation_head"],
    )


def review_preflight(
    output: Path,
    *,
    source_dir: Path,
    source_root: str,
    contract_dir: Path,
    contract_root: str,
    dryrun_dir: Path,
    dryrun_root: str,
    dryrun_review_dir: Path,
    dryrun_review_root: str,
) -> str:
    source = _verify(source_dir, source_root, "replacement preflight")
    contract = _verify(contract_dir, contract_root, "replacement contract")
    dryrun = _verify(dryrun_dir, dryrun_root, "semantic dry-run")
    review = _verify(dryrun_review_dir, dryrun_review_root, "semantic dry-run review")
    manifest = object_from(source_dir / "prepared_manifest.json")["clusters"]
    if (
        source["status"] != "passed_before_first_replacement_model_call"
        or source["authority_sha256"] != EXPECTED_AUTHORITY
        or source["selected_manifest_sha256"] != EXPECTED_SELECTED_MANIFEST
        or source["cluster_count"] != 100
        or source["planned_tick_slots"] != 19_200
        or source["start_from_zero"] is not True
        or source["old_partial_reuse"] is not False
        or len(manifest) != 100
        or [row["cluster_index"] for row in manifest] != list(range(100))
        or dryrun["receipt_count"] != 16_128
        or review["receipt_count"] != 16_128
        or source["capacity"]["projected_free_after_persistent_and_peak_bytes"]
        < source["capacity"]["required_free_after_bytes"]
        or source["capacity"]["projected_free_inodes"]
        < source["capacity"]["required_free_inodes"]
        or output.resolve()
        != Path(contract["contract"]["exact_dirs"]["preflight_review"])
    ):
        raise ValueError("independent replacement preflight review failed")
    for row in manifest:
        cluster = int(row["cluster_index"])
        prepared = source_dir / "prepared" / f"{cluster:03d}"
        if (
            _file_sha(prepared / "source_record.json")
            != row["source_record_file_sha256"]
            or _file_sha(prepared / "latent_manifest.json")
            != row["latent_manifest_sha256"]
            or object_from(prepared / "source_record.json")[
                "source_record_sha256"
            ]
            != row["source_record_sha256"]
        ):
            raise ValueError("prepared source/latent binding drifted")
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "replacement_preflight_review_v1"
        ),
        "status": "independent_preflight_review_passed_before_model",
        "authority_sha256": EXPECTED_AUTHORITY,
        "source_root_sha256": source_root,
        "contract_root_sha256": contract_root,
        "semantic_dryrun_root_sha256": dryrun_root,
        "semantic_dryrun_review_root_sha256": dryrun_review_root,
        "cluster_count": 100,
        "planned_tick_slots": 19_200,
        "start_from_zero": True,
        "old_partial_reuse": False,
        "capacity_and_zero_overlap": True,
        "producer_manifest_adapter_decision_oracle_imported": False,
        "model_pool_selector_calls": 0,
    }
    return _write(
        output,
        report,
        role="preflight_review",
        source_root=source_root,
        implementation_head=contract["implementation_head"],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    closeout = sub.add_parser("closeout")
    closeout.add_argument("--output", type=Path, required=True)
    closeout.add_argument("--source-dir", type=Path, required=True)
    closeout.add_argument("--source-root", required=True)
    contract = sub.add_parser("contract")
    contract.add_argument("--output", type=Path, required=True)
    contract.add_argument("--source-dir", type=Path, required=True)
    contract.add_argument("--source-root", required=True)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("--output", type=Path, required=True)
    matrix.add_argument("--source-dir", type=Path, required=True)
    matrix.add_argument("--source-root", required=True)
    matrix.add_argument("--contract-dir", type=Path, required=True)
    matrix.add_argument("--contract-root", required=True)
    dryrun = sub.add_parser("dryrun")
    dryrun.add_argument("--output", type=Path, required=True)
    dryrun.add_argument("--source-dir", type=Path, required=True)
    dryrun.add_argument("--source-root", required=True)
    dryrun.add_argument("--contract-dir", type=Path, required=True)
    dryrun.add_argument("--contract-root", required=True)
    dryrun.add_argument("--source-materialization-dir", type=Path, required=True)
    dryrun.add_argument("--source-materialization-root", required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--output", type=Path, required=True)
    preflight.add_argument("--source-dir", type=Path, required=True)
    preflight.add_argument("--source-root", required=True)
    preflight.add_argument("--contract-dir", type=Path, required=True)
    preflight.add_argument("--contract-root", required=True)
    preflight.add_argument("--dryrun-dir", type=Path, required=True)
    preflight.add_argument("--dryrun-root", required=True)
    preflight.add_argument("--dryrun-review-dir", type=Path, required=True)
    preflight.add_argument("--dryrun-review-root", required=True)
    args = parser.parse_args()
    if args.command == "closeout":
        root = review_closeout(
            args.output, source_dir=args.source_dir, source_root=args.source_root
        )
    elif args.command == "contract":
        root = review_contract(
            args.output, source_dir=args.source_dir, source_root=args.source_root
        )
    elif args.command == "matrix":
        root = review_matrix(
            args.output,
            source_dir=args.source_dir,
            source_root=args.source_root,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
        )
    elif args.command == "dryrun":
        root = review_dryrun(
            args.output,
            source_dir=args.source_dir,
            source_root=args.source_root,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
            source_materialization_dir=args.source_materialization_dir,
            source_materialization_root=args.source_materialization_root,
        )
    else:
        root = review_preflight(
            args.output,
            source_dir=args.source_dir,
            source_root=args.source_root,
            contract_dir=args.contract_dir,
            contract_root=args.contract_root,
            dryrun_dir=args.dryrun_dir,
            dryrun_root=args.dryrun_root,
            dryrun_review_dir=args.dryrun_review_dir,
            dryrun_review_root=args.dryrun_review_root,
        )
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
