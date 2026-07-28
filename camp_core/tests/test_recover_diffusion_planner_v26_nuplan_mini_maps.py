from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/integrations/recover_diffusion_planner_v26_nuplan_mini_maps.py"


def _module():
    spec = importlib.util.spec_from_file_location("v26_mini_recovery", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _zip(path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, value in files.items():
            archive.writestr(name, value)


def test_separate_staging_explicitly_assembles_matching_shared_license(tmp_path: Path) -> None:
    module = _module()
    maps = tmp_path / "maps.zip"
    mini = tmp_path / "mini.zip"
    sqlite_header = b"SQLite format 3\x00" + b"fixture"
    _zip(
        maps,
        {
            "LICENSE": b"same",
            "maps/nuplan-maps-v1.0.json": b"{}",
            "maps/sample.gpkg": sqlite_header,
        },
    )
    _zip(
        mini,
        {
            "LICENSE": b"same",
            "data/cache/mini/mini.db": sqlite_header,
        },
    )

    maps_info = module.validate_archive(
        maps,
        expected_bytes=maps.stat().st_size,
        expected_sha256=module.sha256_path(maps),
        label="maps",
    )
    assert maps_info["file_member_count"] == 3
    maps_stage = tmp_path / "maps.stage"
    mini_stage = tmp_path / "mini.stage"
    dataset_stage = tmp_path / "dataset.stage"
    module.extract_archive_to_fresh_stage(maps, maps_stage)
    module.extract_archive_to_fresh_stage(mini, mini_stage)
    assembly = module.assemble_staged_archives(maps_stage, mini_stage, dataset_stage)
    assert assembly["shared_file_count"] == 1
    assert (dataset_stage / "LICENSE").read_bytes() == b"same"
    assert (dataset_stage / "maps/sample.gpkg").read_bytes() == sqlite_header
    layout = module.validate_official_mini_layout(dataset_stage)
    assert layout == {
        "official_mini_db_layout": "data/cache/mini",
        "official_mini_db_count": 1,
        "map_gpkg_count": 1,
        "maps_manifest_path": "maps/nuplan-maps-v1.0.json",
    }


def test_official_mini_layout_rejects_placeholder_split_path(tmp_path: Path) -> None:
    module = _module()
    dataset = tmp_path / "dataset"
    (dataset / "nuplan-v1.1/splits/mini").mkdir(parents=True)
    with pytest.raises(ValueError, match="official mini DB root missing"):
        module.validate_official_mini_layout(dataset)


def test_explicit_assembly_rejects_mismatched_shared_member(tmp_path: Path) -> None:
    module = _module()
    maps = tmp_path / "maps.zip"
    mini = tmp_path / "mini.zip"
    _zip(maps, {"LICENSE": b"map-license"})
    _zip(mini, {"LICENSE": b"mini-license"})
    maps_stage = tmp_path / "maps.stage"
    mini_stage = tmp_path / "mini.stage"
    module.extract_archive_to_fresh_stage(maps, maps_stage)
    module.extract_archive_to_fresh_stage(mini, mini_stage)
    with pytest.raises(ValueError, match="shared archive member differs"):
        module.assemble_staged_archives(maps_stage, mini_stage, tmp_path / "dataset.stage")
