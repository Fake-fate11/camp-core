from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLAN = (
    ROOT
    / "docs"
    / "superpowers"
    / "plans"
    / "2026-07-14-v21-native-simulator-paired-closed-loop-tdd.md"
)


def test_plan_is_test_first_and_surgical() -> None:
    text = " ".join(PLAN.read_text(encoding="utf-8").split()).lower()
    required = (
        "write the failing test",
        "run it and confirm the expected failure",
        "implement the minimum",
        "no diffusion-planner file is edited",
        "diffusion_planner_v21_native.py",
        "run_diffusion_planner_dp_camp_v21_native.py",
        "diffusion_planner_v21_native_smoke.json",
    )
    for phrase in required:
        assert phrase.lower() in text


def test_plan_covers_contract_metrics_hook_and_capability_slices() -> None:
    text = " ".join(PLAN.read_text(encoding="utf-8").split()).lower()
    required = (
        "task 1: causal input and k=8 contracts",
        "task 2: native hook and immutable selection",
        "task 3: safetycost native v1 materialization",
        "task 4: paired runner and frozen smoke config",
        "task 5: gate d capability smoke",
        "task 6: gate e tiny paired smoke",
        "candidate 0 exact identity",
        "native lanelet2 five-point",
        "independent result review",
    )
    for phrase in required:
        assert phrase.lower() in text


def test_plan_keeps_claim_and_execution_boundaries() -> None:
    text = " ".join(PLAN.read_text(encoding="utf-8").split()).lower()
    required = (
        "no training in gates c-e",
        "no holdout access",
        "formal seeds 11/12/13 remain forbidden",
        "smoke cannot support a claim",
        "max_steps=64",
        "sg_smooth_enabled=false",
        "dump_npz_dir=null",
    )
    for phrase in required:
        assert phrase.lower() in text
