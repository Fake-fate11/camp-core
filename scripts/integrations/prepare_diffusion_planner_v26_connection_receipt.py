"""Materialize one nonsecret, receipt-bound V26 remote connection profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "camp_core"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v26_connection_receipt import (  # noqa: E402
    build_connection_receipt,
    load_verified_monitor_binding,
    write_connection_receipt,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--connection-profile-id", required=True)
    parser.add_argument("--secure-wrapper-reference", required=True)
    parser.add_argument("--secure-wrapper-sha256", required=True)
    parser.add_argument("--credential-target-reference", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--endpoint-hostname", required=True)
    parser.add_argument("--endpoint-port", type=int, required=True)
    parser.add_argument("--host-key-algorithm", required=True)
    parser.add_argument("--host-key-fingerprint-sha256", required=True)
    parser.add_argument("--camp-checkout", required=True)
    parser.add_argument("--fixed-dp-repo", required=True)
    parser.add_argument("--acquisition-root", required=True)
    parser.add_argument("--union-root", required=True)
    parser.add_argument("--worker-lock", required=True)
    parser.add_argument("--worker-pid", type=int, required=True)
    parser.add_argument("--worker-identity", required=True)
    parser.add_argument("--camp-head", required=True)
    parser.add_argument("--fixed-dp-head", required=True)
    parser.add_argument("--launch-record-reference", required=True)
    parser.add_argument("--created-at", required=True)
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> dict[str, str]:
    receipt = build_connection_receipt(
        connection_profile_id=args.connection_profile_id,
        secure_wrapper_reference=args.secure_wrapper_reference,
        secure_wrapper_sha256=args.secure_wrapper_sha256,
        credential_target_reference=args.credential_target_reference,
        username=args.username,
        endpoint_hostname=args.endpoint_hostname,
        endpoint_port=args.endpoint_port,
        host_key_algorithm=args.host_key_algorithm,
        host_key_fingerprint_sha256=args.host_key_fingerprint_sha256,
        camp_checkout=args.camp_checkout,
        fixed_dp_repo=args.fixed_dp_repo,
        acquisition_root=args.acquisition_root,
        union_root=args.union_root,
        worker_lock=args.worker_lock,
        worker_pid=args.worker_pid,
        worker_identity=args.worker_identity,
        camp_head=args.camp_head,
        fixed_dp_head=args.fixed_dp_head,
        launch_record_reference=args.launch_record_reference,
        created_at=args.created_at,
    )
    receipt_sha256 = write_connection_receipt(path=args.output, receipt=receipt)
    binding = load_verified_monitor_binding(
        receipt_path=args.output,
        expected_receipt_sha256=receipt_sha256,
        expected_connection_profile_id=args.connection_profile_id,
    )
    return {
        "receipt_path": str(args.output.resolve()),
        "receipt_sha256": receipt_sha256,
        "connection_profile_id": binding["connection_profile_id"],
        "connection_receipt_content_sha256": binding["connection_receipt_content_sha256"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    print(json.dumps(run(parse_args(argv)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
