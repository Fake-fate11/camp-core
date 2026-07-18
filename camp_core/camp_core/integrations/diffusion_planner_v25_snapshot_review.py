from __future__ import annotations

import hashlib
import json
import lzma
from pathlib import Path
from typing import Any


SNAPSHOT_SUFFIX = ".json.xz"


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("snapshot JSON has a duplicate key")
        value[key] = item
    return value


def independently_read_snapshot(path: Path, expected_sha256: str) -> Any:
    if (
        type(expected_sha256) is not str
        or len(expected_sha256) != 64
        or set(expected_sha256) - set("0123456789abcdef")
        or path.is_symlink()
        or not path.is_file()
        or path.name != f"{expected_sha256}{SNAPSHOT_SUFFIX}"
    ):
        raise ValueError("snapshot content-address path is invalid")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError("snapshot compressed content-address SHA drifted")
    try:
        raw = lzma.decompress(data, format=lzma.FORMAT_XZ)
    except lzma.LZMAError as exc:
        raise ValueError("snapshot XZ stream is invalid") from exc
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_no_duplicates,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"nonfinite JSON token: {token}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("snapshot JSON is invalid") from exc
    if _canonical_bytes(value) != raw:
        raise ValueError("snapshot JSON bytes are noncanonical")
    return value
