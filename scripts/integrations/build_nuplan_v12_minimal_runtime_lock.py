#!/usr/bin/env python3
"""Convert a pip dry-run report into the reviewed nuPlan runtime hash lock."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple
from urllib.parse import urlparse


FORBIDDEN_PACKAGES = {
    "docker",
    "grpcio",
    "grpcio-tools",
    "pytorch-lightning",
    "ray",
    "tensorboard",
    "timm",
    "torch",
    "torch-scatter",
    "torchmetrics",
    "torchvision",
}


def canonical_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _direct_requirements(lines: Iterable[str]) -> Dict[str, str]:
    requirements: Dict[str, str] = {}
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if "==" not in line:
            raise ValueError(f"direct requirement is not exact: {line}")
        name, version = line.split("==", 1)
        requirements[canonical_name(name.strip())] = version.strip()
    return requirements


def build_lock(
    report: Mapping[str, Any], direct_requirement_lines: Iterable[str]
) -> Tuple[List[str], Dict[str, Any]]:
    direct = _direct_requirements(direct_requirement_lines)
    resolved: Dict[str, str] = {}
    lock: List[str] = []

    for item in report.get("install", []):
        metadata = item["metadata"]
        name = canonical_name(metadata["name"])
        version = str(metadata["version"])
        if name in FORBIDDEN_PACKAGES:
            raise ValueError(f"forbidden package: {name}")
        if name in resolved:
            raise ValueError(f"duplicate package: {name}")

        download = item["download_info"]
        url = str(download["url"])
        if not urlparse(url).path.lower().endswith(".whl"):
            raise ValueError(f"not a wheel: {name}")
        sha256 = download.get("archive_info", {}).get("hashes", {}).get("sha256")
        if not sha256:
            raise ValueError(f"missing sha256: {name}")

        resolved[name] = version
        lock.append(f"{name}=={version} --hash=sha256:{sha256}")

    missing = sorted(
        name for name, version in direct.items() if resolved.get(name) != version
    )
    if missing:
        raise ValueError(f"missing direct requirements: {', '.join(missing)}")

    lock.sort()
    summary = {
        "direct_requirement_count": len(direct),
        "resolved_package_count": len(resolved),
        "wheel_only": True,
        "sha256_complete": True,
        "forbidden_packages": [],
        "missing_direct_requirements": [],
    }
    return lock, summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--direct-requirements", type=Path, required=True)
    parser.add_argument("--lock-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args(argv)

    report = json.loads(args.report.read_text(encoding="utf-8"))
    direct = args.direct_requirements.read_text(encoding="utf-8").splitlines()
    lock, summary = build_lock(report, direct)
    args.lock_output.write_text("\n".join(lock) + "\n", encoding="utf-8")
    args.summary_output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
