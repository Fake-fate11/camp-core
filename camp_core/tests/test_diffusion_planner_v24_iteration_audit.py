from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DESIGN = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-07-15-v24-independent-lanelet2-source-control-design.md"
)


def test_v24_design_keeps_source_failures_local() -> None:
    text = DESIGN.read_text(encoding="utf-8")
    for phrase in (
        "Source-local terminal states never imply a global stop.",
        "Branch A failure cannot close Branch B.",
        "global_stop_authorized",
        "all authorized sources finish per-source map, route, and K=8 paired-support accounting",
        "No new runtime controller abstraction is introduced",
    ):
        assert phrase in text
