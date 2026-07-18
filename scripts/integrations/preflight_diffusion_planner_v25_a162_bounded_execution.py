#!/usr/bin/env python3
"""Seal the A1.6.2 route-level bounded execution plan without running K8."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_a162_bounded_execution import (  # noqa: E402
    PLAN_SCHEMA_VERSION,
    build_route_level_bounded_execution_plan,
    canonical_sha256,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
)


SCHEMA_VERSION = "camp_dp_v25_a162_bounded_execution_preflight_v2"
FORMAL_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_controlled_corpus_source_freeze_retry2_ff028387_"
    "20260717T140842CST"
)
FORMAL_ROOT_SHA256 = (
    "c4dbd49c5fde36302046c6386ca1b8d9cdcaa922976f08230e6227962cc1e531"
)
SOURCE_PAYLOADS = sorted(
    {
        "COMMAND",
        "HEADS",
        "formal_route_source_contract_supplement.json",
        "report.json",
        "route_signal_source_receipts.json",
        "run.exit",
    }
)
SOURCE_REVIEW_PAYLOADS = sorted({"COMMAND", "HEADS", "report.json", "run.exit"})


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, text=True, capture_output=True
    ).stdout.strip()


def _load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write(path: Path, value: Any) -> None:
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


def build(args: argparse.Namespace) -> dict[str, Any]:
    camp_head = _git(ROOT, "rev-parse", "HEAD")
    if _git(ROOT, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("CAMP tracked worktree is dirty")
    if (
        _git(args.dp_repo, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(args.dp_repo, "status", "--porcelain")
    ):
        raise ValueError("fixed DP drifted or is not fully clean")
    formal_seal = verify_complete_seal(
        FORMAL_ARTIFACT, FORMAL_ROOT_SHA256, label="V25 formal corpus"
    )
    source_seal = verify_complete_seal(
        args.source_artifact,
        args.source_root_sha256,
        label="A1.6.2 route source census",
    )
    source_review_seal = verify_complete_seal(
        args.source_review_artifact,
        args.source_review_root_sha256,
        label="A1.6.2 route source census review",
    )
    if (
        source_seal["manifest_paths"] != SOURCE_PAYLOADS
        or source_review_seal["manifest_paths"] != SOURCE_REVIEW_PAYLOADS
        or (args.source_artifact / "run.exit").read_bytes() != b"0\n"
        or (args.source_review_artifact / "run.exit").read_bytes() != b"0\n"
    ):
        raise ValueError("A1.6.2 route source inventory/exit drifted")
    source_report = _load(args.source_artifact / "report.json")
    source_review = _load(args.source_review_artifact / "report.json")
    source_payload = _load(
        args.source_artifact / "route_signal_source_receipts.json"
    )
    formal = _load(FORMAL_ARTIFACT / "controlled_corpus_final_plan.json")
    if (
        source_report.get("status")
        != "passed_source_only_route_signal_authority_census"
        or source_review.get("status")
        != "passed_independent_route_signal_source_review"
        or source_review.get("camp_source_head") != camp_head
        or source_review.get("fixed_dp_head") != FIXED_DP_HEAD
        or source_review.get("reviewed_root_sha256") != args.source_root_sha256
        or Path(str(source_review.get("reviewed_artifact"))).resolve()
        != args.source_artifact.resolve()
        or source_payload.get("camp_source_head") != camp_head
        or source_payload.get("fixed_dp_head") != FIXED_DP_HEAD
        or source_payload.get("source_failures") != []
        or formal.get("train") is None
    ):
        raise ValueError("A1.6.2 route source/formal authority drifted")
    plan = build_route_level_bounded_execution_plan(
        formal_train=formal["train"],
        source_rows=source_payload["cases"],
        source_root_sha256=args.source_root_sha256,
        source_review_root_sha256=args.source_review_root_sha256,
    )
    if (
        plan.get("schema_version") != PLAN_SCHEMA_VERSION
        or plan.get("status") != "passed_preflight_plan_k8_execute_closed"
        or plan.get("unique_identity_count") != 243
        or plan.get("run_count") != 244
        or plan.get("snapshot_capacity") != 15616
        or len(plan.get("tie_equivalence_proofs", [])) != 4
        or any(
            proof.get("all_terminal_items_equivalent") is not True
            for proof in plan["tie_equivalence_proofs"]
        )
    ):
        raise ValueError("A1.6.2 bounded plan live coverage contract drifted")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_bounded_execution_plan_preflight_k8_execute_closed",
        "camp_source_head": camp_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "dp_repo": str(args.dp_repo.resolve()),
        "formal_artifact": str(FORMAL_ARTIFACT),
        "formal_root_sha256": formal_seal["root_sha256"],
        "source_artifact": str(args.source_artifact.resolve()),
        "source_root_sha256": source_seal["root_sha256"],
        "source_review_artifact": str(args.source_review_artifact.resolve()),
        "source_review_root_sha256": source_review_seal["root_sha256"],
        "plan_sha256": canonical_sha256(plan),
        "unique_identity_count": plan["unique_identity_count"],
        "run_count": plan["run_count"],
        "snapshot_capacity": plan["snapshot_capacity"],
        "tie_proof_count": len(plan["tie_equivalence_proofs"]),
        "all_tie_proofs_equivalent": True,
        "k8_executed": False,
        "candidate_generation_started": False,
        "model_loaded": False,
        "simulator_started": False,
        "full_r_started": False,
        "training_executed": False,
        "calibration_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
        "next_gate": "ultra_read_only_a162_bounded_plan_review_before_any_k8",
        "bounded_execution_plan": plan,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-artifact", type=Path, required=True)
    parser.add_argument("--source-root-sha256", required=True)
    parser.add_argument("--source-review-artifact", type=Path, required=True)
    parser.add_argument("--source-review-root-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        report = build(args)
        _write(args.output_dir / "bounded_execution_plan.json", report["bounded_execution_plan"])
        summary = dict(report)
        summary.pop("bounded_execution_plan")
        _write(args.output_dir / "report.json", summary)
        (args.output_dir / "HEADS").write_text(
            f"camp_source_head={report['camp_source_head']}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(
            " ".join(sys.argv) + "\n", encoding="utf-8"
        )
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        root_sha256 = seal_artifact(args.output_dir, label="A1.6.2 bounded plan")
        print(json.dumps({**summary, "artifact_root_sha256": root_sha256}, sort_keys=True))
    except Exception as exc:
        if not (args.output_dir / "SHA256SUMS").exists():
            _write(
                args.output_dir / "failure.json",
                {
                    "schema_version": "camp_dp_v25_a162_bounded_plan_failure_v1",
                    "status": "failed_closed_before_k8",
                    "failure_type": type(exc).__name__,
                    "failure_reason": str(exc),
                    "k8_executed": False,
                    "candidate_generation_started": False,
                    "fresh_b2_opened": False,
                    "outcome_fields_consumed": [],
                },
            )
            (args.output_dir / "HEADS").write_text(
                f"camp_source_head={_git(ROOT, 'rev-parse', 'HEAD')}\n"
                f"fixed_dp_head={FIXED_DP_HEAD}\n",
                encoding="ascii",
            )
            (args.output_dir / "COMMAND").write_text(
                " ".join(sys.argv) + "\n", encoding="utf-8"
            )
            (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
            seal_artifact(args.output_dir, label="failed A1.6.2 bounded plan")
        raise


if __name__ == "__main__":
    main()
