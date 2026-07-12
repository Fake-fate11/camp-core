from __future__ import annotations

import importlib

import pytest


def _module():
    try:
        return importlib.import_module(
            "scripts.integrations.build_nuplan_v12_minimal_runtime_lock"
        )
    except ModuleNotFoundError:
        pytest.fail("the nuPlan minimal runtime lock builder is missing")


def _item(name: str, version: str, *, url: str | None = None, sha256: str = "a" * 64):
    return {
        "metadata": {"name": name, "version": version},
        "download_info": {
            "url": url or f"https://example.test/{name}-{version}-py3-none-any.whl",
            "archive_info": {"hashes": {"sha256": sha256}},
        },
    }


def test_build_lock_sorts_canonical_names_and_covers_direct_requirements() -> None:
    module = _module()
    report = {
        "install": [
            _item("Z_Pkg", "2.0", sha256="b" * 64),
            _item("a.pkg", "1.0", sha256="a" * 64),
        ]
    }

    lock, summary = module.build_lock(report, ["z-pkg==2.0", "a.pkg==1.0"])

    assert lock == [
        f"a-pkg==1.0 --hash=sha256:{'a' * 64}",
        f"z-pkg==2.0 --hash=sha256:{'b' * 64}",
    ]
    assert summary == {
        "direct_requirement_count": 2,
        "resolved_package_count": 2,
        "wheel_only": True,
        "sha256_complete": True,
        "forbidden_packages": [],
        "missing_direct_requirements": [],
    }


def test_build_lock_rejects_missing_sha256() -> None:
    module = _module()
    item = _item("numpy", "1.23.4")
    item["download_info"]["archive_info"]["hashes"] = {}

    with pytest.raises(ValueError, match="missing sha256"):
        module.build_lock({"install": [item]}, ["numpy==1.23.4"])


def test_build_lock_rejects_non_wheel_artifact() -> None:
    module = _module()

    with pytest.raises(ValueError, match="not a wheel"):
        module.build_lock(
            {"install": [_item("retry", "0.9.2", url="https://example.test/retry-0.9.2.tar.gz")]},
            ["retry==0.9.2"],
        )


def test_build_lock_rejects_forbidden_package() -> None:
    module = _module()

    with pytest.raises(ValueError, match="forbidden package"):
        module.build_lock({"install": [_item("torch", "1.9.0")]}, ["torch==1.9.0"])


def test_build_lock_rejects_missing_direct_requirement() -> None:
    module = _module()

    with pytest.raises(ValueError, match="missing direct requirements: scipy"):
        module.build_lock({"install": [_item("numpy", "1.23.4")]}, ["numpy==1.23.4", "scipy==1.9.1"])
