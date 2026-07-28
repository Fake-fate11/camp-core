from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/integrations/acquire_diffusion_planner_v26_nuplan_three_city_raw.py"
SPEC = importlib.util.spec_from_file_location("v26_three_city_acquire", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _city(city: str, archive_bytes: int) -> dict[str, object]:
    role = "city_held_out_ood" if city == "singapore" else "iid_grouped_source"
    family = {
        "boston": "us-ma-boston",
        "pittsburgh": "us-pa-pittsburgh-hazelwood",
        "singapore": "sg-one-north",
    }[city]
    return {
        "city": city,
        "map_family": family,
        "academic_role": role,
        "archive_status": "official_identity_verified",
        "archive_url": f"https://example.test/nuplan-v1.1_train_{city}.zip",
        "archive_filename": f"nuplan-v1.1_train_{city}.zip",
        "content_length": archive_bytes,
        "etag": f'"{city}-etag"',
        "last_modified": "2024-01-30T22:00:00Z",
        "accept_ranges": "bytes",
        "content_type": "application/zip",
    }


def _config() -> dict[str, object]:
    return {
        "city_archives": [
            _city("boston", 38161149300),
            _city("pittsburgh", 30620248893),
            _city("singapore", 34959594178),
        ]
    }


def _metadata() -> dict[str, dict[str, int]]:
    return {
        "boston": {"archive_bytes": 38161149300, "unpacked_total_bytes": 68450083559},
        "pittsburgh": {"archive_bytes": 30620248893, "unpacked_total_bytes": 55726412519},
        "singapore": {"archive_bytes": 34959594178, "unpacked_total_bytes": 62683837159},
    }


def test_config_requires_exact_frozen_three_city_sources() -> None:
    normalized = MODULE._validate_archive_config(_config())
    assert set(normalized) == {"boston", "pittsburgh", "singapore"}
    invalid = _config()
    invalid["city_archives"][0]["archive_url"] += "?signed=secret"  # type: ignore[index]
    with pytest.raises(ValueError, match="signed/query"):
        MODULE._validate_archive_config(invalid)


def test_capacity_projection_uses_serial_delete_zip_minimum() -> None:
    projection = MODULE.capacity_projection(
        _metadata(), ("boston", "singapore", "pittsburgh")
    )
    assert projection["archive_total_bytes"] == 103740992371
    assert projection["unpacked_total_bytes"] == 186860333237
    assert projection["all_archives_retained_and_unpacked_peak_bytes"] == 290601325608
    assert projection["chosen_serial_peak_bytes"] == 217480582130
    assert ["boston", "singapore", "pittsburgh"] in projection["minimum_peak_orders"]


def test_capacity_projection_rejects_duplicate_or_partial_city_order() -> None:
    with pytest.raises(ValueError, match="exactly once"):
        MODULE.capacity_projection(_metadata(), ("boston", "boston", "singapore"))


def test_zip_extraction_rejects_unsafe_member_path(tmp_path: Path) -> None:
    assert MODULE._safe_relative_member("data/cache/mini/example.db") == Path(
        "data/cache/mini/example.db"
    )
    with pytest.raises(ValueError, match="unsafe ZIP member"):
        MODULE._safe_relative_member("../escape.db")


def test_remaining_capacity_after_completed_prefix_does_not_redownload_it() -> None:
    metadata = _metadata()
    assert MODULE._remaining_peak(
        ("boston", "singapore", "pittsburgh"), metadata, completed=1
    ) == 149030498571


def test_central_directory_counts_files_separately_from_directory_entries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr("data/", b"")
        stream.writestr("data/a.txt", b"alpha")
        stream.writestr("b.txt", b"bravo")
    payload = archive.read_bytes()

    def range_fixture(_url: str, start: int, end: int) -> bytes:
        return payload[start : end + 1]

    monkeypatch.setattr(MODULE, "_read_range", range_fixture)
    metadata = MODULE.inspect_zip_central_directory(
        {"archive_url": "https://example.test/fixture.zip", "content_length": len(payload)}
    )
    assert metadata["member_count"] == 3
    assert metadata["file_member_count"] == 2
    assert metadata["directory_member_count"] == 1
    assert metadata["unpacked_total_bytes"] == len(b"alpha") + len(b"bravo")
