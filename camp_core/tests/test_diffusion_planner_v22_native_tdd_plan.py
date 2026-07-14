from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLAN = (
    ROOT
    / "docs"
    / "superpowers"
    / "plans"
    / "2026-07-14-v22-native-route-family-safety-tdd.md"
)


def _plan_text() -> str:
    return " ".join(PLAN.read_text(encoding="utf-8").split()).lower()


def test_plan_is_test_first_surgical_and_reuses_native_runner() -> None:
    text = _plan_text()
    required = (
        "write the failing test",
        "run it and confirm the expected failure",
        "implement the minimum",
        "no diffusion-planner file is edited",
        "run_diffusion_planner_dp_camp_v21_native.py",
        "no parallel native runner",
        "preserve the v21 default behavior",
    )
    for phrase in required:
        assert phrase in text


def test_plan_covers_shared_boundary_metrics_split_and_training() -> None:
    text = _plan_text()
    required = (
        "task 1: source-valid materialization",
        "task 2: v22 affine selection and all-k-high-risk receipts",
        "task 3: speed protocol and retained failure rows",
        "task 4: route-family/corridor census and split freeze",
        "task 5: native decision corpus",
        "task 6: convex learning curve and calibration freeze",
        "task 7: capability and pilot preregistration",
        "task 8: main holdout, statistics, and closeout",
        "5k/10k/20k/50k",
        "0/0.05/0.1/0.2 m/s",
        "cluster bootstrap",
    )
    for phrase in required:
        assert phrase in text


def test_plan_preserves_scientific_and_execution_guards() -> None:
    text = _plan_text()
    required = (
        "fixed k=8 candidate tensor",
        "candidate 0 exact identity",
        "map id, route id, or split identity",
        "before any camp or dp outcome",
        "hard-invalid route remains in the denominator",
        "formal seeds 11/12/13 remain forbidden",
        "full36 remains forbidden",
        "pilot cannot support the final claim",
        "no unseen-map generalization claim",
        "honest no-claim",
    )
    for phrase in required:
        assert phrase in text
