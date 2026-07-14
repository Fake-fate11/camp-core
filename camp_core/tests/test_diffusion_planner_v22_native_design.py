from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DESIGN = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-07-14-v22-native-route-family-safety-design.md"
)


def _design_text() -> str:
    return " ".join(DESIGN.read_text(encoding="utf-8").split()).lower()


def test_design_freezes_route_family_split_before_outcomes() -> None:
    text = _design_text()
    required = (
        "logical maps may be reused across train, calibration, and holdout",
        "route-family/corridor group",
        "route identity, route family, and seed namespace",
        "connected components",
        "shared lanelet",
        "overlapping corridor",
        "topology family",
        "before any camp or dp outcome",
        "record-level random split is forbidden",
    )
    for phrase in required:
        assert phrase in text


def test_design_retains_every_preregistered_route_and_failure() -> None:
    text = _design_text()
    required = (
        "no deletion, replacement, redraw, or skip",
        "all-k-high-risk/stress",
        "source-valid mask",
        "must not force candidate 0",
        "hard-invalid route remains in the denominator",
        "route coverage",
        "hard-invalid rate",
        "paired-complete rate",
    )
    for phrase in required:
        assert phrase in text


def test_design_preserves_fixed_dp_affine_selector_boundary() -> None:
    text = _design_text()
    required = (
        "fixed k=8 candidate tensor",
        "score_k(w)=a_k^t w",
        "nonnegative simplex",
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "candidate 0",
        "dp modification is a hard stop",
        "map id, route id, and split identity",
    )
    for phrase in required:
        assert phrase in text


def test_design_limits_claim_and_preregisters_scale_and_speed() -> None:
    text = _design_text()
    required = (
        "within the two fixed logical maps",
        "unseen route-family/corridor and seed",
        "no unseen-map generalization claim",
        "future external-validation extension",
        "30 routes x 3",
        "100 routes x 5",
        "5k/10k/20k/50k",
        "0/0.05/0.1/0.2 m/s",
        "0.1 m/s",
        "formal seeds 11/12/13",
        "full36",
    )
    for phrase in required:
        assert phrase in text
