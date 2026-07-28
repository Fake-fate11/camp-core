"""Run one receipt-bound, read-only status projection for the V26 successor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "camp_core"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v26_connection_receipt import (  # noqa: E402
    load_verified_monitor_binding,
)


def _quote(value: str) -> str:
    return shlex.quote(value)


def _readonly_remote_command(binding: Mapping[str, Any]) -> str:
    """Build a bounded inspection command from receipt-bound fixed targets only."""

    remote = binding["canonical_remote"]
    pid = int(binding["launch_worker"]["pid"])
    acquisition_root = _quote(str(remote["acquisition_root"]))
    union_root = _quote(str(remote["union_root"]))
    worker_lock = _quote(str(remote["worker_lock"]))
    return f"""set -u
PID={pid}
OUT={acquisition_root}
UNION={union_root}
LOCK={worker_lock}
printf 'pid_status='; if kill -0 \"$PID\" 2>/dev/null; then printf 'running\\n'; ps -p \"$PID\" -o pid=,stat=,etime=; else printf 'not_running\\n'; fi
printf 'acquisition_root='; test -d \"$OUT\" && printf 'present\\n' || printf 'absent\\n'
printf 'union_root='; test -d \"$UNION\" && printf 'present\\n' || printf 'absent\\n'
printf 'lock='; test -e \"$LOCK\" && printf 'present\\n' || printf 'absent\\n'
if test -d \"$OUT/units\"; then printf 'unit_json_count='; find \"$OUT/units\" -maxdepth 1 -type f -name '*.json' | wc -l; fi
printf 'terminal_artifacts\\n'; find \"$OUT\" \"$UNION\" -maxdepth 2 -type f \\( -name run.exit -o -name run.status.json -o -name raw_receipt.json -o -name report.json -o -iname '*terminal*.json' \\) -printf '%p %s\\n' 2>/dev/null | sort
if test -f \"$OUT/run.exit\"; then printf 'run_exit='; head -c 512 \"$OUT/run.exit\"; printf '\\n'; fi
printf 'parent_execution_exception_unit_count='; (grep -R -l --include='*.json' 'ParentExecutionException' \"$OUT/units\" 2>/dev/null || true) | wc -l
printf 'gpu_compute\\n'; nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader,nounits 2>&1 || true
printf 'disk_bytes\\n'; df -B1 /root/autodl-tmp | tail -n 1
printf 'stderr_tail\\n'; ERR=$(find \"$OUT\" -maxdepth 2 -type f \\( -iname '*stderr*' -o -name stderr.log \\) -print -quit 2>/dev/null); if test -n \"${{ERR:-}}\"; then tail -n 30 \"$ERR\"; else printf 'not_found\\n'; fi
"""


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connection-receipt", type=Path, required=True)
    parser.add_argument("--expected-receipt-sha256", required=True)
    parser.add_argument("--expected-connection-profile-id", required=True)
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> dict[str, Any]:
    binding = load_verified_monitor_binding(
        receipt_path=args.connection_receipt,
        expected_receipt_sha256=args.expected_receipt_sha256,
        expected_connection_profile_id=args.expected_connection_profile_id,
    )
    payload = {
        "commands": [
            {
                "name": "v26_stage8b_successor_receipt_bound_readonly_status",
                "command": _readonly_remote_command(binding),
                "timeout": 45,
            }
        ]
    }
    wrapper = binding["secure_wrapper"]["reference"]
    completed = subprocess.run(
        [sys.executable, wrapper],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.stdout:
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("safe connection wrapper returned non-JSON output") from exc
    else:
        result = {
            "credential_read": False,
            "host_key_verified": False,
            "error_type": "SafeWrapperNoOutput",
        }
    result["connection_profile_id"] = binding["connection_profile_id"]
    result["connection_receipt_content_sha256"] = binding[
        "connection_receipt_content_sha256"
    ]
    result["transport_status"] = (
        "ok" if completed.returncode == 0 and result.get("host_key_verified") else "WAIT_NONBLOCKING"
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    print(json.dumps(run(parse_args(argv)), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
