#!/usr/bin/env python3
"""Seal the 2026-07-17 Ultra Stage-A decision as machine authority."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
)
from scripts.integrations.review_diffusion_planner_v25_stage_a0_authority import (  # noqa: E402
    PASSED_PREFLIGHT_ROOT,
    PASSED_REVIEW_ROOT,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (  # noqa: E402
    FORMAL_ROOT_SHA256,
    SUPERSEDED_PARTIAL_CORPUS_ROOT,
    _git_head,
    _tracked_dirty,
)


SCHEMA_VERSION = "camp_dp_v25_ultra_stage_a14_r04_decision_v5"
A0_ROOT = "b8664cd074bf48ded82017950616c851a3f3ca6afdd6fbe0ba0e705359e8ff41"
SUPERSEDED_LEDGER_ROOT = (
    "05449b7a8913559575347763aa95f25b4a9e5e9f58b5dc6106251a9e1b4c7fa2"
)
SUPERSEDED_VALIDATION_ROOT = (
    "e07bfcbd879d992b1a9ad61d467a7970bcc19b120303e457e244899bb0316a72"
)
SUPERSEDED_A1_R0_ROOTS = [
    "b75898b2d9263abf157ebd72b8d03e445ceeb23168a06d8065ae0b959aa3340d",
    "f8ecaf1a9235753245cad736cef4172e8a553143a0eff45bf179add2b4ecdac5",
    "947d4b00fe39222e8be581e3d681959ed153f6410c7c065adb5b992c9de89d58",
    "69f02664fa96fe9689b60f6432e0c910b9a18bb6ffd1a88f569c10670178d3be",
    "c8b8b926bd63a0a8185d7ea3f422e7b94bc0c40921560e6576ac9e4b0ca786e9",
    "209fc00b6aeb90d887f9cc2871fefdcd619d0b1086d6ffb3ee3c0ac39911f11d",
    "e948eb17e3561a93c803ec8485d725d47e341b129a794bcf1c2c6e9593cef946",
    # Ultra A1.1/R0.1 review kept these seven immutable but downgraded the
    # branch-cut-affected chain to superseded diagnostic evidence.
    "d98929000c09cbe1f3bcdc7f57290091e0be31e67726f4920d201bc98292897e",
    "836d5468fd05cdbd837037352d14cd20fb21a6b653ece41272bb85b30c42ad82",
    "a37fd179db35ab51b4ca08c99e669c3b62ecb5804a3679fafd9b35450d618352",
    "e099837be509085fd761244ca676d387ee4debfe0214cf22057b631ba4dff1fa",
    "e28c5851d15a0d313afe2f577c13ed9207686fa0a724d1738514675aae0fbb1e",
    "a520f86c2930fb3c2535efb730bf2e2a1b33db11c77f50535926f1971dbcf07c",
    "81a0c1acf7f5c5b76315659b7c917fb641013db20b5a130c27e2402a6560fb6b",
    # Ultra semantic-v3 review kept these roots immutable but blocked them from
    # release-chain use because canonical bytes/self-lock/reviewer independence
    # still required the bounded A1.2/R0.2 correction.
    "010f644cc106cb63b479845fa67b59985575df14d9583d7f9164816ac885e73c",
    "9a7d0b663b5946eb4180f707198e3372d9f20a85dd6eea70ba035ce276a362e5",
    "85cd4513721e5c8546934aedb34a39fcdb4c99a1318cd2c1fa1fc722acb893bc",
    "ae728cd3781fce5f01afae0bd3411d051e2b657e52b7044de10f3d5b4a8d5b8a",
    "485e00fcf063f745d415c34e1d762cac62deca84abf027cfa48d8e830cb6ec52",
    "b7dc7fe00d21af71caba172eac9edf5500fb967e7379b712024600c62b9e5458",
    "6eee9f157d1668ad37120b3a9542f1e5b5661f9077b0fb15cdb5e4a4b43f35d2",
    # Ultra A1.2/R0.2 review kept these roots immutable but blocked them from
    # release-chain use because the snapshot writer, seven-root exact values,
    # and independent formal universe still required A1.3/R0.3 correction.
    "9735a52763e7ef61f516c65445d4f02057cf0fb0beda443354b07e6d69cbe54e",
    "76b21380fb66ffb2d90f6bd9adbccf887ea34458caf3383226ea8d17f6a1a833",
    "6e5847cf600048948e778330dd7aad3d7ea8aeb44f0e7e1070a83782114e87dd",
    "b705b826324a449eab87af36a1dd9325f3f773ebe6a3b14f8b437dc45478e7c8",
    "04d28ed769625f3db23ba2e9646384014817d4bb58196efae358ee2230677682",
    "1e84bf5bf35fa0dfea601b4e304b863cfabd0a5d3b1b8ee74e2cb7115c1f60cd",
    "27086204937a9501979bfcdb943be31f7e2be45d60bb7710508633e2af39bcfa",
    # Ultra A1.3/R0.3 review preserved these type-clean roots but blocked their
    # release-chain use because type-smuggling and nested-schema bypasses remained.
    "1b2dd591e342fdfa0d88f05a2d2537bc8f51292d71502a22e701147cee15488c",
    "02529652c60e5843c2bb5568222291e5e3b5884fc218ab2e3cd0884810620ae4",
    "e2f7f484bdbb18d9eac7963cc7737cc6f39fc6427deb39e07a62060a9ecdc2a0",
    "c7375c3539727abf7b5a726b437bcb643de96fcbf2911b966bfa5e13f20881f8",
    "7d6308d5f3b36a3ec3925ffe1a3ef929f5e45940429e117b8fe52837a4e2f332",
    "50ae46bb76f76e07bac6a91405e30cade7bdfd715cf417a6e7d5931cdaaa3878",
    "c07e1c4cd63db8aaa21118925e7a78bbb2b6c1687ecbaf4939047057863979b1",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def _bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    head = _git_head(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("CAMP tracked worktree is dirty")
    decision = {
        "schema_version": SCHEMA_VERSION,
        "status": "A1_4_R0_4_only_released",
        "decision_date": "2026-07-18",
        "source_thread_id": "019f6eee-8fc2-75f3-843c-75562f610b13",
        "corrected_source_head": head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "s01_preflight_root_sha256": PASSED_PREFLIGHT_ROOT,
        "s01_review_root_sha256": PASSED_REVIEW_ROOT,
        "a0_root_sha256": A0_ROOT,
        "formal_root_sha256": FORMAL_ROOT_SHA256,
        "rejected_roots": [SUPERSEDED_PARTIAL_CORPUS_ROOT],
        "superseded_diagnostic_roots": [
            SUPERSEDED_LEDGER_ROOT,
            SUPERSEDED_VALIDATION_ROOT,
            *SUPERSEDED_A1_R0_ROOTS,
        ],
        "progress_reference": "source_valid_candidate_set_reference",
        "progress_formula": "r=max(progress[j] where source_valid[j]); progress_shortfall[k]=max(r-progress[k],0)",
        "selection_eligibility": "source_valid",
        "empty_source_valid": "fail_closed",
        "candidate0_or_all_k_fallback_allowed": False,
        "a1_4_authorized": True,
        "r0_4_source_authority_preflight_authorized": True,
        "bounded_21red_1nosignal_x64_authorized_after_source_pass": True,
        "full_r_authorized": False,
        "monitor_authorized": False,
        "training_authorized": False,
        "calibration_authorized": False,
        "scene_runtime_authorized": False,
        "v2i_authorized": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    (args.output_dir / "decision.json").write_bytes(_bytes(decision))
    (args.output_dir / "HEADS").write_text(
        f"camp_head={head}\nfixed_dp_head={FIXED_DP_HEAD}\n", encoding="ascii"
    )
    (args.output_dir / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
    root = seal_artifact(args.output_dir, label="V25 Ultra Stage-A decision")
    print(json.dumps({"status": decision["status"], "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
