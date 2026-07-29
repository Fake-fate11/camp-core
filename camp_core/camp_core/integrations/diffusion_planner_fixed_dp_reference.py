"""Neutral fixed-DP identity and array-fingerprint helpers for CAMP."""

from __future__ import annotations

import hashlib

import numpy as np


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def training_parameter_array_sha256(value: np.ndarray) -> str:
    """Preserve the frozen producer fingerprint byte-for-byte."""
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(b"\0")
    digest.update(",".join(str(item) for item in array.shape).encode("ascii"))
    digest.update(b"\0")
    digest.update(array.tobytes())
    return digest.hexdigest()
