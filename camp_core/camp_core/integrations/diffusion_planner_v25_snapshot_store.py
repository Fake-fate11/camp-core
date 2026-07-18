from __future__ import annotations

import json
import lzma
from typing import Any


SNAPSHOT_SUFFIX = ".json.xz"
SNAPSHOT_CODEC = "canonical-json-utf8-single-lf-xz6-sha256-v1"


def canonical_snapshot_json_bytes(value: Any) -> bytes:
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


def encode_snapshot(value: Any) -> bytes:
    return lzma.compress(
        canonical_snapshot_json_bytes(value),
        format=lzma.FORMAT_XZ,
        check=lzma.CHECK_SHA256,
        preset=6,
    )


def decode_snapshot_for_roundtrip(data: bytes) -> Any:
    try:
        raw = lzma.decompress(data, format=lzma.FORMAT_XZ)
    except lzma.LZMAError as exc:
        raise ValueError("snapshot XZ stream is invalid") from exc
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("snapshot JSON is invalid") from exc
    if canonical_snapshot_json_bytes(value) != raw:
        raise ValueError("snapshot JSON bytes are noncanonical")
    return value
