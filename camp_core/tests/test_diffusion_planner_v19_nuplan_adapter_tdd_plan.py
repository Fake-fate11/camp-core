from pathlib import Path


PLAN = Path(
    "docs/superpowers/plans/"
    "2026-07-12-v19-nuplan-adapter-default-provenance-tdd.md"
)


def test_v19_adapter_tdd_plan_freezes_required_evidence_and_names() -> None:
    text = PLAN.read_text(encoding="utf-8")

    for value in (
        "47497ef353b5c0df1a0c6cef08031444e88ae793",
        "7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "ce3c323af01c0d7ec5672f7832ef53f9c679aab0",
        "816367a0eec1b0e0563a1d09c0b8b988f9d407bef3f99678bd01ebc2d1f83f8c",
        "4bad5fa9fe5e00033860870a6b0eafe50c8e3e195eea0d74c46430bfdc516031",
        "DP-default deterministic/MAP baseline",
        "native_ranked_top1=false",
    ):
        assert value in text


def test_v19_adapter_tdd_plan_freezes_fail_closed_candidate_contract() -> None:
    text = PLAN.read_text(encoding="utf-8")

    for value in (
        "candidates `[8,80,4]`",
        "noise_scale=1.0",
        "score_k(w)=a_k^T w",
        "pre-score and post-score candidate SHA",
        "never force candidate 0",
        "never recompute `progress_shortfall` from all K",
        "32 dynamic plus 5 static observable objects",
    ):
        assert value in text


def test_v19_adapter_tdd_plan_is_nonexecuting() -> None:
    text = PLAN.read_text(encoding="utf-8")

    for value in (
        "authorizes no simulator execution",
        "holdout access",
        "adapter execution",
        "real checkpoint inference",
        "safety/ADE/FDE/latency metric generation",
    ):
        assert value in text
