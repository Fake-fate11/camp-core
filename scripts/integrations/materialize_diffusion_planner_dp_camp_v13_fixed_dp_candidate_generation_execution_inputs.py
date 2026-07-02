#!/usr/bin/env python3
"""Materialize fixed-DP candidate generation execution inputs.

This utility prepares a read-only input contract for a later execution
preflight. It writes a valid-set JSON and provenance registries for approved
fixed-DP npz sources. It never runs Diffusion Planner, changes DP files, reads
closed-loop outcomes, trains CAMP, or authorizes deployment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SCHEMA_VERSION = "dp_camp_v13_fixed_dp_candidate_generation_execution_inputs_materialization_v1"
READY_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_execution_inputs_materialized"
REJECT_STATUS = "dp_camp_v13_fixed_dp_candidate_generation_execution_inputs_rejected"
APPROVED_SOURCE_KIND = "fresh_nonformal_fixed_dp_npz"
ZERO_OVERLAP_KEYS = (
    "candidate_tensor_hash",
    "path_signature",
    "record_identity",
    "split_manifest_root",
)
FORBIDDEN_SOURCE_PATTERNS = (
    r"full36",
    r"formal[_-]?seed[_-]?11",
    r"formal[_-]?seed[_-]?12",
    r"formal[_-]?seed[_-]?13",
    r"seed[_-]?11",
    r"seed[_-]?12",
    r"seed[_-]?13",
    r"closed[_-]?loop",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source_npz", action="append", type=Path, required=True)
    parser.add_argument("--approved_source_manifest_json", type=Path)
    parser.add_argument("--source_manifest_root", required=True)
    parser.add_argument("--fixed_dp_checkpoint", type=Path, required=True)
    parser.add_argument("--fixed_dp_args_json", type=Path, required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        source_npz=args.source_npz,
        approved_source_manifest_json=args.approved_source_manifest_json,
        source_manifest_root=args.source_manifest_root,
        fixed_dp_checkpoint=args.fixed_dp_checkpoint,
        fixed_dp_args_json=args.fixed_dp_args_json,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        output_dir=args.output_dir,
    )
    if report["final_decision"]["passed"]:
        write_materialized_inputs(report, args.output_dir)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    source_npz: list[Path],
    approved_source_manifest_json: Path | None,
    source_manifest_root: str,
    fixed_dp_checkpoint: Path,
    fixed_dp_args_json: Path,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    output_dir: Path,
) -> dict[str, Any]:
    manifest = _load_manifest(approved_source_manifest_json)
    files = [path.resolve() for path in source_npz]
    records = [_record(path=path, source_manifest_root=source_manifest_root) for path in files]
    checks = _checks(
        files=files,
        approved_source_manifest_json=approved_source_manifest_json,
        manifest=manifest,
        source_manifest_root=source_manifest_root,
        fixed_dp_checkpoint=fixed_dp_checkpoint,
        fixed_dp_args_json=fixed_dp_args_json,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        records=records,
        output_dir=output_dir,
    )
    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    valid_set_list = output_dir / "valid_set_list.json"
    return {
        "schema_version": SCHEMA_VERSION,
        "input_contract": {
            "approved_source_kind": APPROVED_SOURCE_KIND,
            "source_manifest_root": source_manifest_root,
            "source_npz_files": [str(path) for path in files],
            "valid_set_list": str(valid_set_list),
            "valid_set_files": [str(path) for path in files],
            "fixed_dp_checkpoint": str(fixed_dp_checkpoint),
            "fixed_dp_args_json": str(fixed_dp_args_json),
            "records": records,
            "required_zero_overlap_keys": list(ZERO_OVERLAP_KEYS),
            "candidate_tensor_hashes": [record["candidate_tensor_hash"] for record in records],
            "path_signatures": [record["path_signature"] for record in records],
            "record_identities": [record["record_identity"] for record in records],
            "split_manifest_roots": [record["split_manifest_root"] for record in records],
            "closed_loop_outcome_read": False,
            "dp_modification": False,
            "fixed_dp_candidate_generation_executed": False,
            "candidate_generation_by_camp": False,
            "score_expression": SCORE_EXPRESSION,
        },
        "checks": checks,
        "final_decision": _decision(passed=passed, failed=failed),
    }


def write_materialized_inputs(report: dict[str, Any], output_dir: Path) -> None:
    contract = _dict(report.get("input_contract"))
    output_dir.mkdir(parents=True, exist_ok=True)
    valid_set_list = Path(str(contract["valid_set_list"]))
    valid_set_list.write_text(
        json.dumps({"files": contract["valid_set_files"]}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _checks(
    *,
    files: list[Path],
    approved_source_manifest_json: Path | None,
    manifest: dict[str, Any],
    source_manifest_root: str,
    fixed_dp_checkpoint: Path,
    fixed_dp_args_json: Path,
    current_dp_head: str,
    required_dp_head: str,
    records: list[dict[str, str]],
    output_dir: Path,
) -> list[dict[str, Any]]:
    manifest_files = {str(Path(item).resolve()) for item in _list(manifest.get("files"))}
    checks = [
        _expect("source_npz_nonempty", bool(files), True),
        _expect("source_manifest_root_nonempty", bool(source_manifest_root.strip()), True),
        _expect("current_dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _expect("fixed_dp_checkpoint_exists", fixed_dp_checkpoint.is_file(), True),
        _expect("fixed_dp_args_json_exists", fixed_dp_args_json.is_file(), True),
        _expect("output_dir_not_preexisting", output_dir.exists(), False),
        _expect("approved_source_manifest_kind", manifest.get("approved_source_kind"), APPROVED_SOURCE_KIND),
    ]
    if approved_source_manifest_json is not None:
        checks.append(_expect("approved_source_manifest_exists", approved_source_manifest_json.is_file(), True))
    for path in files:
        normalized = str(path)
        lower = normalized.lower()
        checks.extend(
            [
                _expect(f"source_npz_exists_{_slug(normalized)}", path.is_file(), True),
                _expect(f"source_npz_suffix_{_slug(normalized)}", path.suffix, ".npz"),
                _expect(f"source_npz_manifest_approved_{_slug(normalized)}", normalized in manifest_files, True),
            ]
        )
        for pattern in FORBIDDEN_SOURCE_PATTERNS:
            checks.append(
                _expect(
                    f"source_npz_forbids_{_slug(pattern)}_{_slug(normalized)}",
                    re.search(pattern, lower) is not None,
                    False,
                )
            )
    for key in ZERO_OVERLAP_KEYS:
        checks.append(_expect(f"records_include_{key}", all(record.get(key) for record in records), True))
    return checks


def _record(*, path: Path, source_manifest_root: str) -> dict[str, str]:
    tensor_hash = _sha256(path) if path.is_file() else ""
    path_signature = _hash_text(str(path).replace("\\", "/"))
    split_manifest_root = _hash_text(source_manifest_root)
    return {
        "source_npz": str(path),
        "candidate_tensor_hash": tensor_hash,
        "path_signature": path_signature,
        "record_identity": _hash_text("|".join([source_manifest_root, str(path), tensor_hash])),
        "split_manifest_root": split_manifest_root,
    }


def _decision(*, passed: bool, failed: list[str]) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "failed_checks": failed,
        "fixed_dp_candidate_generation_execution_inputs_materialized": passed,
        "fixed_dp_candidate_generation_executed": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "fixed_dp_candidate_generation_execution_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_or_postselection_authorized": False,
        "closed_loop_outcome_authorized": False,
        "data_preparation_authorized_next": False,
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "dp_modification_authorized": False,
        "deployment_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": SCORE_EXPRESSION,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = _dict(report["final_decision"])
    contract = _dict(report["input_contract"])
    return "\n".join(
        [
            "# Fixed-DP Candidate Generation Input Materialization",
            "",
            f"- status: `{decision['status']}`",
            f"- passed: `{decision['passed']}`",
            f"- failed_checks: `{decision['failed_checks']}`",
            f"- valid_set_list: `{contract.get('valid_set_list')}`",
            f"- source_count: `{len(_list(contract.get('source_npz_files')))}`",
            f"- fixed_dp_generation_executed: `{decision['fixed_dp_candidate_generation_executed']}`",
            f"- training_preflight_authorized: `{decision['training_preflight_authorized_next']}`",
            "",
        ]
    )


def _load_manifest(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object at {path}")
    return payload


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": actual == expected, "actual": actual, "expected": expected}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")[:80]


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
