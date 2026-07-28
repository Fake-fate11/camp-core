from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "camp_core"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def _receipt(module, wrapper: Path) -> dict[str, object]:
    return module.build_connection_receipt(
        connection_profile_id="fixture-secure-profile-v1",
        secure_wrapper_reference=str(wrapper),
        secure_wrapper_sha256=module._file_sha256(wrapper),
        credential_target_reference="CredentialManager/fixture",
        username="root",
        endpoint_hostname="fixture.autodl.invalid",
        endpoint_port=52317,
        host_key_algorithm="ssh-ed25519",
        host_key_fingerprint_sha256="SHA256:fixtureFingerprint",
        camp_checkout="/root/autodl-tmp/camp-checkout",
        fixed_dp_repo="/root/autodl-tmp/Diffusion-Planner",
        acquisition_root="/root/autodl-tmp/v26-successor",
        union_root="/root/autodl-tmp/v26-union",
        worker_lock="/root/autodl-tmp/v26.lock",
        worker_pid=426640,
        worker_identity="v26-stage8b-successor-acquisition",
        camp_head="a" * 40,
        fixed_dp_head="b" * 40,
        launch_record_reference="safe-wrapper-launch-record:fixture",
        created_at="2026-07-28T00:00:00Z",
    )


def test_connection_receipt_round_trips_nonsecret_and_binds_wrapper(tmp_path: Path) -> None:
    module = importlib.import_module(
        "camp_core.integrations.diffusion_planner_v26_connection_receipt"
    )
    wrapper = tmp_path / "safe_wrapper.py"
    wrapper.write_text("# fixture safe wrapper\n", encoding="utf-8")
    receipt = _receipt(module, wrapper)
    receipt_path = tmp_path / "receipt.json"
    receipt_sha256 = module.write_connection_receipt(path=receipt_path, receipt=receipt)
    bound = module.load_verified_monitor_binding(
        receipt_path=receipt_path,
        expected_receipt_sha256=receipt_sha256,
        expected_connection_profile_id="fixture-secure-profile-v1",
    )
    serialized = receipt_path.read_text(encoding="utf-8")
    assert bound["launch_worker"]["pid"] == 426640
    assert bound["forbid_endpoint_rediscovery"] is True
    assert bound["secrets_reference_only"] is True
    assert "password" not in serialized.casefold()
    assert "private_key" not in serialized.casefold()
    assert json.loads(serialized) == receipt


def test_connection_consumer_rejects_endpoint_rediscovery_and_profile_drift(tmp_path: Path) -> None:
    module = importlib.import_module(
        "camp_core.integrations.diffusion_planner_v26_connection_receipt"
    )
    wrapper = tmp_path / "safe_wrapper.py"
    wrapper.write_text("# fixture safe wrapper\n", encoding="utf-8")
    receipt_path = tmp_path / "receipt.json"
    receipt_sha256 = module.write_connection_receipt(
        path=receipt_path, receipt=_receipt(module, wrapper)
    )
    with pytest.raises(ValueError, match="endpoint rediscovery"):
        module.load_verified_monitor_binding(
            receipt_path=receipt_path,
            expected_receipt_sha256=receipt_sha256,
            expected_connection_profile_id="fixture-secure-profile-v1",
            endpoint_override="other.endpoint.invalid",
        )
    with pytest.raises(ValueError, match="profile ID drifted"):
        module.load_verified_monitor_binding(
            receipt_path=receipt_path,
            expected_receipt_sha256=receipt_sha256,
            expected_connection_profile_id="other-profile",
        )


def test_connection_receipt_rejects_missing_profile_and_secret_serialization(tmp_path: Path) -> None:
    module = importlib.import_module(
        "camp_core.integrations.diffusion_planner_v26_connection_receipt"
    )
    wrapper = tmp_path / "safe_wrapper.py"
    wrapper.write_text("# fixture safe wrapper\n", encoding="utf-8")
    receipt = _receipt(module, wrapper)
    missing_profile = copy.deepcopy(receipt)
    missing_profile["connection_profile_id"] = ""
    missing_profile["connection_receipt_content_sha256"] = module._receipt_content_sha256(
        missing_profile
    )
    with pytest.raises(ValueError, match="connection_profile_id"):
        module.validate_connection_receipt(missing_profile)

    secret = copy.deepcopy(receipt)
    secret["secure_wrapper"]["password"] = "must-not-serialize"
    secret["connection_receipt_content_sha256"] = module._receipt_content_sha256(secret)
    with pytest.raises(ValueError, match="must not serialize secrets"):
        module.validate_connection_receipt(secret)


def test_connection_receipt_producer_and_monitor_have_no_endpoint_override() -> None:
    producer = importlib.import_module(
        "scripts.integrations.prepare_diffusion_planner_v26_connection_receipt"
    )
    monitor = importlib.import_module(
        "scripts.integrations.monitor_diffusion_planner_v26_stage8b_successor"
    )
    with pytest.raises(SystemExit):
        producer.parse_args(["--endpoint-override", "forbidden"])
    with pytest.raises(SystemExit):
        monitor.parse_args(["--endpoint-override", "forbidden"])
