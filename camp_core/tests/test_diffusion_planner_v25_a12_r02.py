from __future__ import annotations

import hashlib
import inspect
import os
from pathlib import Path
import subprocess
import sys

import pytest

from camp_core.integrations.diffusion_planner_v25_full_r_authority import (
    CANONICAL_JSON_BYTE_SPEC_VERSION,
    canonical_json_bytes,
    canonical_sha256,
)
from scripts.integrations import (
    review_diffusion_planner_v25_full_config_preflight as full_config_reviewer,
    run_diffusion_planner_v25_controlled_training_corpus as corpus,
)


def test_canonical_json_byte_contract_golden_and_independent_roundtrip() -> None:
    assert CANONICAL_JSON_BYTE_SPEC_VERSION == "camp_dp_v25_canonical_json_utf8_lf_v1"
    assert full_config_reviewer.CANONICAL_JSON_BYTE_SPEC_VERSION == (
        CANONICAL_JSON_BYTE_SPEC_VERSION
    )
    golden = b'{"a":1}\n'
    expected = "e346432021b04179518d9614f3560ccd71354a4ee101ddcb893d6959a9d6301c"
    assert canonical_json_bytes({"a": 1}) == golden
    assert corpus._canonical_json_bytes({"a": 1}) == golden
    assert full_config_reviewer._oracle_canonical_json_bytes({"a": 1}) == golden
    assert canonical_sha256({"a": 1}) == expected
    assert corpus._canonical_sha256({"a": 1}) == expected
    assert full_config_reviewer._oracle_sha256({"a": 1}) == expected


@pytest.mark.parametrize(
    "payload",
    [
        {"namespace": "config", "value": [1, 2, 3]},
        {"namespace": "semantic", "value": {"道路": "红灯"}},
        {"namespace": "retained_ineligible", "value": []},
        {"namespace": "seven_roots", "value": {"r01": "0" * 64}},
    ],
)
def test_producer_to_independent_reviewer_canonical_root_namespaces(payload: dict) -> None:
    producer = corpus._canonical_json_bytes(payload)
    reviewer = full_config_reviewer._oracle_canonical_json_bytes(payload)
    assert producer == reviewer
    assert producer.endswith(b"\n") and not producer.endswith(b"\n\n")
    assert hashlib.sha256(producer).hexdigest() == full_config_reviewer._oracle_sha256(
        payload
    )
    for mutated in (producer[:-1], producer + b"\n", producer[:-2] + b"X\n"):
        assert hashlib.sha256(mutated).hexdigest() != hashlib.sha256(producer).hexdigest()


def test_preflight_does_not_probe_free_state_inside_outer_lock() -> None:
    source = inspect.getsource(corpus._preflight)
    assert "_lock_is_free" not in source
    assert "main() already holds TRAIN_LOCK" in source


@pytest.mark.skipif(os.name != "posix", reason="real flock integration is Linux-only")
def test_real_flock_outer_owner_second_process_and_exception_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    lock = tmp_path / "corpus.lock"
    command = [
        sys.executable,
        "-c",
        (
            "from pathlib import Path; "
            "from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus "
            "import _exclusive_lock; "
            f"p=Path({str(lock)!r}); "
            "\ntry:\n with _exclusive_lock(p): pass\nexcept BlockingIOError:\n raise SystemExit(73)"
        ),
    ]
    with corpus._exclusive_lock(lock):
        assert corpus._lock_is_free(lock) is False
        blocked = subprocess.run(command, check=False)
        assert blocked.returncode == 73
        monkeypatch.setattr(
            corpus,
            "build_controlled_train_config",
            lambda *_args: {"selector": {"weights": {"path": "w", "sha256": "a" * 64}}},
        )
        monkeypatch.setattr(corpus, "verify_config_assets", lambda *_args: None)
        monkeypatch.setattr(
            corpus,
            "_shared_assets",
            lambda config: {"selector": config["selector"]},
        )
        monkeypatch.setattr(corpus, "_verify_case_assets_cached", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(
            corpus,
            "_config_authority_receipt",
            lambda _config: {"scenario_id": "1" * 64},
        )
        monkeypatch.setattr(corpus, "_load_formal_plan", lambda: ({"train": []}, "f" * 64))
        monkeypatch.setattr(
            corpus,
            "_retained_ineligible_authority_receipts",
            lambda _plan: [{"scenario_id": f"{index:064x}"} for index in range(153)],
        )
        report = corpus._preflight(
            [{"route_identity_sha256": "1" * 64, "family": "red", "tier": "easy"}],
            {},
            {"1" * 64: {"path": "route", "sha256": "b" * 64}},
            {},
        )
        assert report["status"] == "passed"
        assert report["validated_identity_count"] == 1
    assert corpus._lock_is_free(lock) is True

    with pytest.raises(RuntimeError, match="terminal failure"):
        with corpus._exclusive_lock(lock):
            raise RuntimeError("terminal failure")
    assert corpus._lock_is_free(lock) is True
