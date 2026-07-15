from __future__ import annotations

import hashlib
import importlib
import types
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner import (
    inspect_lanelet2_extended_regulatory_elements,
    require_source_preserving_lanelet2_regulatory_adapter,
)


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "integrations" / "run_diffusion_planner_dp_camp_v21_native.py"


def _write_map(path: Path, *, detection_area: bool) -> bytes:
    regulatory = ""
    reference = ""
    if detection_area:
        reference = '<member type="relation" ref="20" role="regulatory_element"/>'
        regulatory = """
  <relation id="20">
    <member type="way" ref="30" role="refers"/>
    <member type="way" ref="31" role="ref_line"/>
    <tag k="type" v="regulatory_element"/>
    <tag k="subtype" v="detection_area"/>
  </relation>"""
    payload = f"""<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6">
  <node id="1" lat="35.0" lon="139.0"/>
  <relation id="10">
    {reference}
    <tag k="type" v="lanelet"/>
  </relation>{regulatory}
</osm>
""".encode()
    path.write_bytes(payload)
    return payload


def test_adapter_census_records_attached_extended_elements(tmp_path: Path) -> None:
    source = tmp_path / "map.osm"
    payload = _write_map(source, detection_area=True)

    census = inspect_lanelet2_extended_regulatory_elements(source)

    assert census == {
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "regulatory_relation_count": 1,
        "regulatory_subtype_counts": {"detection_area": 1},
        "extended_relation_ids": ["20"],
        "extended_subtype_counts": {"detection_area": 1},
        "extended_lanelet_reference_counts": {"detection_area": 1},
    }


def test_stock_map_does_not_require_official_extension(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "map.osm"
    payload = _write_map(source, detection_area=False)
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda _name: pytest.fail("stock map must not import Autoware extension"),
    )

    receipt = require_source_preserving_lanelet2_regulatory_adapter(source)

    assert receipt["mode"] == "stock_lanelet2"
    assert receipt["required_extended_subtypes"] == []
    assert source.read_bytes() == payload


def test_extended_map_requires_real_official_module_and_preserves_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "map.osm"
    payload = _write_map(source, detection_area=True)
    official = types.SimpleNamespace(
        __file__="/opt/autoware/autoware_lanelet2_extension_python/projection.py",
        MGRSProjector=object(),
    )
    monkeypatch.setattr(importlib, "import_module", lambda _name: official)

    receipt = require_source_preserving_lanelet2_regulatory_adapter(source)

    assert receipt["mode"] == "official_autoware_lanelet2_extension"
    assert receipt["required_extended_subtypes"] == ["detection_area"]
    assert receipt["official_module"] == official.__file__
    assert receipt["source_sha256_before"] == receipt["source_sha256_after"]
    assert source.read_bytes() == payload


def test_projection_fallback_cannot_impersonate_regulatory_registration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "map.osm"
    payload = _write_map(source, detection_area=True)
    fallback = types.SimpleNamespace(MGRSProjector=object())
    monkeypatch.setattr(importlib, "import_module", lambda _name: fallback)

    with pytest.raises(RuntimeError, match="process-local projection fallback"):
        require_source_preserving_lanelet2_regulatory_adapter(source)

    assert source.read_bytes() == payload


def test_missing_official_extension_fails_closed_without_map_rewrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "map.osm"
    payload = _write_map(source, detection_area=True)

    def missing(_name: str):
        raise ModuleNotFoundError("official extension absent")

    monkeypatch.setattr(importlib, "import_module", missing)

    with pytest.raises(RuntimeError, match="official Autoware Lanelet2 extension"):
        require_source_preserving_lanelet2_regulatory_adapter(source)

    assert source.read_bytes() == payload
    assert list(tmp_path.iterdir()) == [source]


def test_native_runner_prepares_regulatory_adapter_before_projection_and_load() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    assert "require_source_preserving_lanelet2_regulatory_adapter" in text
    start = text.index("def run_arm(", text.index("def build_native_arm_runner("))
    end = text.index("def ", start + len("def run_arm("))
    body = text[start:end]

    regulatory = body.index('context["prepare_regulatory"](map_path)')
    projection = body.index('context["install_projection"](map_path)')
    builder = body.index('context["LaneletSceneBuilder"](str(map_path))')
    assert regulatory < projection < builder
    assert "sanitize_lanelet2_map" not in body
