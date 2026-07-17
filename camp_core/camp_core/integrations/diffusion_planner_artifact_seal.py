from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any


_SEAL_FILES = frozenset({"SHA256SUMS", "ROOT_SHA256SUMS"})


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA256 digest")
    return value


def _require_regular_unaliased(path: Path, label: str) -> os.stat_result:
    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise ValueError(f"{label} is missing or unreadable: {path}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise ValueError(f"{label} must not be a symlink: {path}")
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"{label} must be a regular file: {path}")
    return metadata


def _require_no_symlink_path_components(path: Path, *, label: str) -> Path:
    raw = Path(path)
    if not raw.is_absolute() or not raw.anchor:
        raise ValueError(f"{label} must be an absolute path")
    current = Path(raw.anchor)
    components = [current]
    for part in raw.parts[1:]:
        if part in {".", ".."}:
            raise ValueError(f"{label} has an unsafe path component")
        current = current / part
        components.append(current)
    for index, component in enumerate(components):
        try:
            metadata = os.lstat(component)
        except OSError as exc:
            raise ValueError(f"{label} component is missing: {component}") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"{label} contains a symlink component: {component}")
        if index < len(components) - 1 and not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(f"{label} has a non-directory parent: {component}")
    return raw


def _safe_manifest_relative(relative: str, *, label: str) -> PurePosixPath:
    pure = PurePosixPath(relative)
    if (
        not relative
        or pure.is_absolute()
        or any(part in {"", ".", ".."} for part in pure.parts)
        or "\\" in relative
        or pure.as_posix() != relative
        or relative in _SEAL_FILES
    ):
        raise ValueError(f"{label} has an unsafe manifest path: {relative!r}")
    return pure


def _walk_regular_files(root: Path, *, label: str) -> dict[str, Path]:
    files: dict[str, Path] = {}
    stack = [root]
    while stack:
        directory = stack.pop()
        try:
            entries = list(os.scandir(directory))
        except OSError as exc:
            raise ValueError(f"{label} tree cannot be inspected: {directory}") from exc
        for entry in entries:
            path = Path(entry.path)
            try:
                metadata = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise ValueError(f"{label} tree entry is unreadable: {path}") from exc
            if entry.is_symlink():
                raise ValueError(f"{label} contains a symlink: {path}")
            if stat.S_ISDIR(metadata.st_mode):
                stack.append(path)
                continue
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError(f"{label} contains a special node: {path}")
            relative = path.relative_to(root).as_posix()
            files[relative] = path
    return files


def verify_complete_seal(
    root: Path,
    expected_root_sha256: str | None = None,
    *,
    label: str = "artifact",
) -> dict[str, Any]:
    """Verify a complete, exact, non-aliased recursive artifact seal."""

    raw_root = Path(root)
    if not raw_root.is_absolute():
        raw_root = raw_root.absolute()
    raw_root = _require_no_symlink_path_components(raw_root, label=f"{label} root")
    try:
        root_metadata = os.lstat(raw_root)
    except OSError as exc:
        raise ValueError(f"{label} root is missing or unreadable: {raw_root}") from exc
    if stat.S_ISLNK(root_metadata.st_mode):
        raise ValueError(f"{label} root must not be a symlink")
    if not stat.S_ISDIR(root_metadata.st_mode):
        raise ValueError(f"{label} root must be a directory")
    root = raw_root.resolve()
    manifest = root / "SHA256SUMS"
    receipt = root / "ROOT_SHA256SUMS"
    _require_regular_unaliased(manifest, f"{label} manifest")
    _require_regular_unaliased(receipt, f"{label} root receipt")

    manifest_bytes = manifest.read_bytes()
    root_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if expected_root_sha256 is not None:
        expected = _require_sha256(expected_root_sha256, f"{label} expected root")
        if root_sha256 != expected:
            raise ValueError(f"{label} root SHA256 mismatch")
    if receipt.read_bytes() != f"{root_sha256}  SHA256SUMS\n".encode("ascii"):
        raise ValueError(f"{label} ROOT_SHA256SUMS mismatch")
    try:
        manifest_text = manifest_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} SHA256SUMS is not valid UTF-8") from exc

    declared: dict[str, str] = {}
    lines = manifest_text.splitlines()
    if not lines:
        raise ValueError(f"{label} SHA256SUMS must be nonempty")
    for line_number, line in enumerate(lines, start=1):
        if line.count("  ") != 1 or line != line.strip():
            raise ValueError(f"{label} malformed SHA256SUMS line {line_number}")
        digest, relative = line.split("  ", 1)
        _require_sha256(digest, f"{label} manifest digest line {line_number}")
        pure = _safe_manifest_relative(relative, label=label)
        if relative in declared:
            raise ValueError(f"{label} duplicate manifest path: {relative}")
        path = root.joinpath(*pure.parts)
        _require_regular_unaliased(path, f"{label} manifest payload")
        if _sha256_file(path) != digest:
            raise ValueError(f"{label} manifest payload SHA256 mismatch: {relative}")
        declared[relative] = digest

    actual = _walk_regular_files(root, label=label)
    actual_payloads = set(actual) - _SEAL_FILES
    if actual_payloads != set(declared):
        unlisted = sorted(actual_payloads - set(declared))[:8]
        missing = sorted(set(declared) - actual_payloads)[:8]
        raise ValueError(
            f"{label} inventory is inexact (unlisted={unlisted}, missing={missing})"
        )
    return {
        "root": str(root),
        "root_sha256": root_sha256,
        "file_count": len(declared),
        "manifest_paths": sorted(declared),
    }


def seal_artifact(root: Path, *, label: str = "artifact") -> str:
    """Create the canonical seal after rejecting unsafe tree entries."""

    root = Path(root)
    if not root.is_absolute():
        root = root.absolute()
    try:
        metadata = os.lstat(root)
    except OSError as exc:
        raise ValueError(f"{label} root is missing or unreadable: {root}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError(f"{label} root must be a real directory")
    files = _walk_regular_files(root, label=label)
    payloads = {
        relative: path
        for relative, path in files.items()
        if relative not in _SEAL_FILES
    }
    if not payloads:
        raise ValueError(f"{label} payload must be nonempty")
    manifest = root / "SHA256SUMS"
    receipt = root / "ROOT_SHA256SUMS"
    manifest.write_bytes(
        "".join(
            f"{_sha256_file(payloads[relative])}  {relative}\n"
            for relative in sorted(payloads)
        ).encode("utf-8")
    )
    root_sha256 = _sha256_file(manifest)
    receipt.write_bytes(f"{root_sha256}  SHA256SUMS\n".encode("ascii"))
    verify_complete_seal(root, root_sha256, label=label)
    return root_sha256
