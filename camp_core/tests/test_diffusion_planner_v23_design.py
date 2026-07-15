from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DESIGN = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-07-15-v23-lanelet2-native-evidence-design.md"
)


def test_v23_design_freezes_sources_semantics_and_scientific_boundaries() -> None:
    text = " ".join(DESIGN.read_text(encoding="utf-8").split()).lower()
    for phrase in (
        "b8d441c59293e34289cd7bca1ba5e5a33e9189d9",
        "e22f01093fa6516c0552549ada302270329c59a4",
        "source-preserving adapter",
        "detection_area",
        "sanitize_lanelet2_map is forbidden for v23",
        "same map family",
        "overlapping corridor",
        "same route and all of its seeds stay in one split",
        "dp_camp_v10_14d",
        "fixed k=8 candidate tensor",
        "25/50/75/100%",
        "holdout opens once",
        "honest no-claim",
        "promotion, deployment, and online activation are out of scope",
    ):
        assert phrase in text


def test_v23_design_decomposes_work_and_rejects_semantic_deletion() -> None:
    text = " ".join(DESIGN.read_text(encoding="utf-8").split()).lower()
    for phrase in (
        "subproject 1: source and license freeze",
        "subproject 2: map compatibility adapter",
        "subproject 3: map-family, route, and split freeze",
        "subproject 4: corpus, training, paired evaluation, and closeout",
        "official regulatory-element registration",
        "thin process-local registration adapter",
        "deleting unsupported regulatory elements is rejected",
    ):
        assert phrase in text
