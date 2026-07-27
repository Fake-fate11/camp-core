from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camp_core", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_v25_multiroute_review_recovery import (  # noqa: E402
    AUTHORITY_SHA256,
    EVALUATION_ROOT,
    PREFLIGHT_ROOT,
    exact_dirs,
    old_exact_dirs,
)
from camp_core.integrations.diffusion_planner_v25_stage_orchestration import (  # noqa: E402
    artifact_root,
    execute_orchestration,
)


EXECUTION_DIR = (
    "/root/autodl-tmp/"
    "camp_dp_v25_industrial_v3_multiroute_v2_replacement_"
    "8fc8e271_47a47c03_execution"
)
PREFLIGHT_DIR = EXECUTION_DIR.replace("_execution", "_preflight")
INDUSTRIAL_CONTRACT_DIR = (
    "/root/autodl-tmp/"
    "camp_dp_v25_industrial_evaluation_contract_v3_c197c1e5_720e9293"
)
SUPERSEDED_EVALUATION_DIR = (
    "/root/autodl-tmp/"
    "camp_dp_v25_industrial_v3_multiroute_v2_replacement_"
    "8fc8e271_47a47c03_evaluation"
)


def run_phase(
    *,
    phase: str,
    implementation_head: str,
    expected_interpreter: str,
    camp_root: Path,
) -> tuple[str, dict]:
    dirs = exact_dirs(implementation_head)
    python = expected_interpreter
    if phase == "stage-authority":
        return execute_orchestration(
            output=Path(dirs["stage_authority_operation"]),
            mode="producer-and-reviewer",
            implementation_head=implementation_head,
            authority_sha256=AUTHORITY_SHA256,
            expected_interpreter=python,
            cwd=camp_root,
            source_dir=None,
            source_root=None,
            producer_command=[
                python,
                str(
                    camp_root
                    / "scripts/integrations/"
                    "freeze_diffusion_planner_v25_multiroute_"
                    "review_recovery_authority.py"
                ),
                "--output",
                dirs["stage_authority"],
                "--implementation-head",
                implementation_head,
            ],
            producer_target_dir=Path(dirs["stage_authority"]),
            reviewer_command=[
                python,
                str(
                    camp_root
                    / "scripts/integrations/"
                    "review_diffusion_planner_v25_multiroute_"
                    "review_recovery_authority.py"
                ),
                "--output",
                dirs["stage_authority_review"],
                "--source-dir",
                dirs["stage_authority"],
                "--source-root",
                "__SOURCE_ROOT__",
            ],
            reviewer_target_dir=Path(dirs["stage_authority_review"]),
        )
    if phase != "evaluation-review":
        raise ValueError("unknown recovery phase")
    stage_authority_root = artifact_root(Path(dirs["stage_authority"]))
    old = old_exact_dirs()
    return execute_orchestration(
        output=Path(dirs["evaluation_review_operation"]),
        mode="review-only",
        implementation_head=implementation_head,
        authority_sha256=AUTHORITY_SHA256,
        expected_interpreter=python,
        cwd=camp_root,
        source_dir=Path(old["evaluation"]),
        source_root=EVALUATION_ROOT,
        producer_command=None,
        producer_target_dir=None,
        reviewer_command=[
            python,
            str(
                camp_root
                / "scripts/integrations/"
                "review_diffusion_planner_v25_industrial_"
                "multiroute_v2_actor_binding.py"
            ),
            "evaluation",
            "--output",
            dirs["evaluation_review"],
            "--source-dir",
            old["evaluation"],
            "--source-root",
            "__SOURCE_ROOT__",
            "--execution-dir",
            EXECUTION_DIR,
            "--preflight-dir",
            PREFLIGHT_DIR,
            "--preflight-root",
            PREFLIGHT_ROOT,
            "--industrial-contract-dir",
            INDUSTRIAL_CONTRACT_DIR,
            "--superseded-evaluation-dir",
            SUPERSEDED_EVALUATION_DIR,
            "--stage-authority-dir",
            dirs["stage_authority"],
            "--stage-authority-root",
            stage_authority_root,
        ],
        reviewer_target_dir=Path(dirs["evaluation_review"]),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        choices=("stage-authority", "evaluation-review"),
        required=True,
    )
    parser.add_argument("--implementation-head", required=True)
    parser.add_argument("--expected-interpreter", required=True)
    parser.add_argument("--camp-root", type=Path, required=True)
    args = parser.parse_args()
    root, result = run_phase(
        phase=args.phase,
        implementation_head=args.implementation_head,
        expected_interpreter=args.expected_interpreter,
        camp_root=args.camp_root.resolve(),
    )
    print(root)
    return int(result["overall_exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
