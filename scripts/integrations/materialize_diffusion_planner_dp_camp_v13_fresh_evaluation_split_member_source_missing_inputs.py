#!/usr/bin/env python3
"""Materialize missing v13 fresh member-source inputs.

This helper is default-off and fail-closed. When explicitly enabled it reads
only existing fixed-DP current-source artifact/source manifests and training
split-root sources, then writes the candidate member-source manifest and
training split-root registry required by the downstream fresh member-source
materializer. It does not run DP, generate candidates, replay, train CAMP,
modify DP, promote, deploy, or make safety/CAMP-over-DP claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_missing_input_"
    "materializer_v1"
)
DISABLED_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_missing_input_"
    "materializer_default_off_disabled"
)
READY_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_missing_input_"
    "materializer_complete"
)
REJECT_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_missing_input_"
    "materializer_rejected"
)
SOURCE_REVIEW_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_implementation_static_contract_review_v1"
)
SOURCE_REVIEW_PASS_STATUS = (
    "dp_camp_v13_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_implementation_static_contract_review_passed"
)
AUTHORIZED_CURRENT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_implementation_only"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
    "dp_reward_eval_plus_prior_nonoverlap_remediation_static_dp_reward_"
    "training_artifact_shadow_replay_evaluation_nonoverlap_failure_"
    "remediation_fresh_evaluation_split_member_source_materialization_"
    "failure_remediation_post_implementation_static_contract_review_only"
)
MEMBER_MANIFEST_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_member_source_candidates_v1"
)
TRAINING_SPLIT_ROOTS_SCHEMA_VERSION = (
    "dp_camp_v13_training_split_manifest_roots_v1"
)
PROVENANCE_SCHEMA_VERSION = (
    "dp_camp_v13_fresh_member_source_missing_input_provenance_v1"
)
SHA256SUMS_NAME = "SHA256SUMS"
OUTPUT_FILES = (
    "candidate_member_source_manifest.json",
    "training_split_manifest_roots.json",
    "candidate_member_source_manifest_provenance_report.json",
    SHA256SUMS_NAME,
)
MEMBER_FIELDS = (
    "member_id",
    "source_path",
    "route",
    "seed",
    "candidate_tensor_hashes",
    "path_signatures",
    "record_identity_hashes",
    "split_manifest_roots",
)
IDENTITY_FIELDS = (
    "candidate_tensor_hashes",
    "path_signatures",
    "record_identity_hashes",
    "split_manifest_roots",
)
SPLIT_ROOT_KEYS = (
    "split_manifest_roots",
    "split_manifest_root",
    "split_manifest_root_hashes",
    "split_manifest_root_hash",
    "split_root",
    "split_roots",
)
REJECTED_SOURCE_KEYS = (
    "candidate_tensor_hashes",
    "path_signatures",
    "record_identity_hashes",
    "split_manifest_roots",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Default-off materializer for missing v13 member-source inputs."
    )
    parser.add_argument("--implementation_static_contract_review_json", type=Path, required=True)
    parser.add_argument("--expected_static_contract_review_sha256", required=True)
    parser.add_argument("--candidate_source_manifest_json", type=Path, required=True)
    parser.add_argument("--training_split_root_sources_json", type=Path, required=True)
    parser.add_argument("--rejected_overlap_source_registry_manifest_json", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--authorized_current_work", default=AUTHORIZED_CURRENT_WORK)
    parser.add_argument("--authorized_next_work", default=AUTHORIZED_NEXT_WORK)
    parser.add_argument(
        "--enable_v13_fresh_evaluation_split_member_source_missing_input_materializer",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        implementation_static_contract_review_json=(
            args.implementation_static_contract_review_json
        ),
        expected_static_contract_review_sha256=(
            args.expected_static_contract_review_sha256
        ),
        candidate_source_manifest_json=args.candidate_source_manifest_json,
        training_split_root_sources_json=args.training_split_root_sources_json,
        rejected_overlap_source_registry_manifest_json=(
            args.rejected_overlap_source_registry_manifest_json
        ),
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        authorized_current_work=args.authorized_current_work,
        authorized_next_work=args.authorized_next_work,
        enabled=args.enable_v13_fresh_evaluation_split_member_source_missing_input_materializer,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["status"] != REJECT_STATUS else 1


def build_report(
    *,
    implementation_static_contract_review_json: Path,
    expected_static_contract_review_sha256: str,
    candidate_source_manifest_json: Path,
    training_split_root_sources_json: Path,
    rejected_overlap_source_registry_manifest_json: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    authorized_current_work: str = AUTHORIZED_CURRENT_WORK,
    authorized_next_work: str = AUTHORIZED_NEXT_WORK,
    enabled: bool = False,
) -> dict[str, Any]:
    paths = {
        "implementation_static_contract_review_json": (
            implementation_static_contract_review_json.resolve()
        ),
        "candidate_source_manifest_json": candidate_source_manifest_json.resolve(),
        "training_split_root_sources_json": training_split_root_sources_json.resolve(),
        "rejected_overlap_source_registry_manifest_json": (
            rejected_overlap_source_registry_manifest_json.resolve()
        ),
        "output_dir": output_dir.resolve(),
    }
    report = _base_report(
        paths=paths,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        enabled=enabled,
    )
    checks = _preflight_checks(
        paths=paths,
        expected_static_contract_review_sha256=expected_static_contract_review_sha256,
        current_camp_head=current_camp_head,
        current_camp_origin_main=current_camp_origin_main,
        current_dp_head=current_dp_head,
        required_dp_head=required_dp_head,
        authorized_current_work=authorized_current_work,
    )
    if not enabled:
        return _finish(
            report=report,
            checks=checks,
            status=DISABLED_STATUS,
            passed=True,
            authorized_current_work=authorized_current_work,
            authorized_next_work=None,
        )
    members, member_errors, member_sources = _load_candidate_members(
        paths["candidate_source_manifest_json"],
        paths["rejected_overlap_source_registry_manifest_json"],
    )
    split_roots, split_errors, split_sources = _load_training_split_roots(
        paths["training_split_root_sources_json"]
    )
    checks.extend(
        [
            _check("candidate_members_nonempty", bool(members), len(members), ">0"),
            _check("training_split_roots_nonempty", bool(split_roots), len(split_roots), ">0"),
        ]
    )
    checks.extend(_error_checks("candidate_member", member_errors))
    checks.extend(_error_checks("training_split_root", split_errors))
    passed = all(check["passed"] for check in checks)
    if passed:
        paths["output_dir"].mkdir(parents=True, exist_ok=True)
        _write_json(
            paths["output_dir"] / "candidate_member_source_manifest.json",
            {
                "schema_version": MEMBER_MANIFEST_SCHEMA_VERSION,
                "members": members,
            },
        )
        _write_json(
            paths["output_dir"] / "training_split_manifest_roots.json",
            {
                "schema_version": TRAINING_SPLIT_ROOTS_SCHEMA_VERSION,
                "split_manifest_roots": split_roots,
            },
        )
        _write_json(
            paths["output_dir"] / "candidate_member_source_manifest_provenance_report.json",
            {
                "schema_version": PROVENANCE_SCHEMA_VERSION,
                "candidate_member_count": len(members),
                "training_split_manifest_root_count": len(split_roots),
                "candidate_member_sources": member_sources,
                "training_split_root_sources": split_sources,
                "candidate_operation": "fixed DP candidate reranking only",
                "score_expression": SCORE_EXPRESSION,
            },
        )
        _write_sha256sums(paths["output_dir"], OUTPUT_FILES[:-1])
    report["materialized_outputs"] = _output_summary(paths["output_dir"])
    return _finish(
        report=report,
        checks=checks,
        status=READY_STATUS if passed else REJECT_STATUS,
        passed=passed,
        authorized_current_work=authorized_current_work,
        authorized_next_work=authorized_next_work if passed else None,
        member_count=len(members),
        split_root_count=len(split_roots),
    )


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# V13 Missing Member-Source Input Materializer",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Enabled: `{decision['enabled']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Candidate members: `{decision['candidate_member_count']}`",
        f"- Training split roots: `{decision['training_split_manifest_root_count']}`",
        "",
        "This gate reads only existing fixed-DP current-source artifacts and "
        "training split-root sources. It does not run DP, generate candidates, "
        "replay, train CAMP, modify DP, promote, deploy, or make safety claims.",
        "",
    ]
    return "\n".join(lines)


def _base_report(
    *,
    paths: dict[str, Path],
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    enabled: bool,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "default_off": True,
            "enabled": enabled,
            "input_materialization": enabled,
            "fixed_dp_candidate_generation": False,
            "candidate_generation_by_camp": False,
            "trajectory_generation_by_camp": False,
            "trajectory_modification_by_camp": False,
            "dp_modification": False,
            "replay_execution": False,
            "training_execution": False,
            "selector_promotion": False,
            "deployment": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": SCORE_EXPRESSION,
        },
        "heads": {
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "inputs": {name: str(path) for name, path in paths.items()},
        "source_hashes": {
            name: _sha256(path) for name, path in paths.items() if path.is_file()
        },
        "materialized_outputs": _output_summary(paths["output_dir"]),
    }


def _preflight_checks(
    *,
    paths: dict[str, Path],
    expected_static_contract_review_sha256: str,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str,
    authorized_current_work: str,
) -> list[dict[str, Any]]:
    review = _load_json_dict(paths["implementation_static_contract_review_json"])
    decision = _dict(review.get("final_decision"))
    checks = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "git sha"),
        _expect("camp_head_matches_origin_main", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("candidate_source_manifest_json_exists", paths["candidate_source_manifest_json"].is_file(), str(paths["candidate_source_manifest_json"]), "file exists"),
        _check("training_split_root_sources_json_exists", paths["training_split_root_sources_json"].is_file(), str(paths["training_split_root_sources_json"]), "file exists"),
        _check("rejected_overlap_source_registry_manifest_json_exists", paths["rejected_overlap_source_registry_manifest_json"].is_file(), str(paths["rejected_overlap_source_registry_manifest_json"]), "file exists"),
        _expect("static_review_sha256", _sha256(paths["implementation_static_contract_review_json"]), expected_static_contract_review_sha256),
        _expect("static_review_schema", review.get("schema_version"), SOURCE_REVIEW_SCHEMA_VERSION),
        _expect("static_review_status", decision.get("status"), SOURCE_REVIEW_PASS_STATUS),
        _expect("static_review_passed", decision.get("passed"), True),
        _expect("static_review_authorizes_this_gate", decision.get("authorized_next_work"), authorized_current_work),
        _expect("static_review_implementation_authorized", decision.get("materialization_failure_remediation_implementation_authorized_next"), True),
    ]
    for flag in (
        "training_execution_authorized_next",
        "replay_execution_authorized_next",
        "fixed_dp_candidate_generation_authorized_next",
        "candidate_generation_by_camp_authorized",
        "trajectory_generation_by_camp_authorized",
        "trajectory_modification_by_camp_authorized",
        "dp_modification_authorized",
        "selector_promotion_authorized",
        "deployment_authorized",
        "safety_benefit_claim_authorized",
        "camp_over_dp_top1_claim_authorized",
    ):
        checks.append(_expect(f"static_review_blocks_{flag}", decision.get(flag), False))
    return checks


def _load_candidate_members(
    source_manifest_path: Path,
    rejected_registry_manifest_path: Path,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    source_manifest = _load_json_dict(source_manifest_path)
    rejected_sets = _load_rejected_sets(rejected_registry_manifest_path)
    source_paths = [Path(path) for path in _list(source_manifest.get("source_json_paths"))]
    raw_members = _list(source_manifest.get("members")) + _list(source_manifest.get("candidate_members"))
    errors: list[str] = []
    provenance: list[str] = []
    for path in source_paths:
        payload = _load_json_dict(path)
        if not payload:
            errors.append(f"unreadable_source:{path}")
            continue
        raw_members.extend(_list(payload.get("members")))
        raw_members.extend(_list(payload.get("candidate_members")))
        provenance.append(str(path))
    members: list[dict[str, Any]] = []
    seen: set[str] = set()
    for idx, raw in enumerate(raw_members):
        member = _normalize_member(raw, idx)
        member_errors = _member_errors(member, rejected_sets)
        if member_errors:
            errors.extend(member_errors)
            continue
        if member["member_id"] in seen:
            continue
        seen.add(member["member_id"])
        members.append(member)
    return members, errors, provenance


def _normalize_member(raw: Any, idx: int) -> dict[str, Any]:
    data = _dict(raw)
    return {
        "member_id": str(data.get("member_id") or data.get("id") or f"member_{idx}"),
        "source_path": str(data.get("source_path") or ""),
        "route": str(data.get("route") or data.get("scenario") or ""),
        "seed": data.get("seed"),
        "candidate_tensor_hashes": _string_list(data.get("candidate_tensor_hashes") or data.get("candidate_tensor_hash")),
        "path_signatures": _string_list(data.get("path_signatures") or data.get("path_signature")),
        "record_identity_hashes": _string_list(data.get("record_identity_hashes") or data.get("record_identity_hash")),
        "split_manifest_roots": _string_list(data.get("split_manifest_roots") or data.get("split_manifest_root")),
    }


def _member_errors(member: dict[str, Any], rejected_sets: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []
    for field in MEMBER_FIELDS:
        value = member.get(field)
        if value in (None, "", []) or (field == "seed" and value is None):
            errors.append(f"missing_{field}:{member.get('member_id')}")
    route = str(member.get("route") or "").lower()
    source_path = str(member.get("source_path") or "").lower()
    seed = member.get("seed")
    if seed in (11, 12, 13):
        errors.append(f"formal_seed:{member.get('member_id')}")
    if "full36" in route or "full36" in source_path:
        errors.append(f"full36:{member.get('member_id')}")
    for field in IDENTITY_FIELDS:
        if set(member[field]) & rejected_sets[field]:
            errors.append(f"rejected_overlap_{field}:{member.get('member_id')}")
    return errors


def _load_rejected_sets(path: Path) -> dict[str, set[str]]:
    payload = _load_json_dict(path)
    sets = {field: set(_string_list(payload.get(field))) for field in REJECTED_SOURCE_KEYS}
    for key, target in (
        ("candidate_tensor_hash_registry_json", "candidate_tensor_hashes"),
        ("path_signature_registry_json", "path_signatures"),
        ("record_identity_hash_registry_json", "record_identity_hashes"),
        ("split_manifest_root_registry_json", "split_manifest_roots"),
    ):
        registry = payload.get(key)
        if registry:
            sets[target].update(_extract_strings(_load_json_dict(Path(registry))))
    return sets


def _load_training_split_roots(source_path: Path) -> tuple[list[str], list[str], list[str]]:
    payload = _load_json_dict(source_path)
    source_paths = [Path(path) for path in _list(payload.get("source_json_paths"))]
    roots = set(_extract_split_roots(payload))
    errors: list[str] = []
    provenance = [str(source_path)]
    for path in source_paths:
        item = _load_json_dict(path)
        if not item:
            errors.append(f"unreadable_split_root_source:{path}")
            continue
        roots.update(_extract_split_roots(item))
        provenance.append(str(path))
    return sorted(roots), errors, provenance


def _extract_split_roots(value: Any) -> list[str]:
    roots: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in SPLIT_ROOT_KEYS:
                roots.extend(_string_list(item))
            roots.extend(_extract_split_roots(item))
    elif isinstance(value, list):
        for item in value:
            roots.extend(_extract_split_roots(item))
    return sorted(set(root for root in roots if root))


def _extract_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(_extract_strings(item))
        return strings
    if isinstance(value, dict):
        strings: list[str] = []
        for item in value.values():
            strings.extend(_extract_strings(item))
        return strings
    return []


def _error_checks(prefix: str, errors: list[str]) -> list[dict[str, Any]]:
    return [_check(f"{prefix}_errors_empty", not errors, errors, [])]


def _finish(
    *,
    report: dict[str, Any],
    checks: list[dict[str, Any]],
    status: str,
    passed: bool,
    authorized_current_work: str,
    authorized_next_work: str | None,
    member_count: int = 0,
    split_root_count: int = 0,
) -> dict[str, Any]:
    failed = [check["name"] for check in checks if not check["passed"]]
    final_passed = bool(passed and not failed)
    report["checks"] = checks
    report["final_decision"] = {
        "status": status if final_passed or status == DISABLED_STATUS else REJECT_STATUS,
        "passed": final_passed,
        "failed_checks": failed,
        "authorized_current_work": authorized_current_work,
        "authorized_next_work": authorized_next_work if final_passed else None,
        "enabled": report["analysis"]["enabled"],
        "candidate_member_count": member_count,
        "training_split_manifest_root_count": split_root_count,
        "candidate_member_source_manifest_written": final_passed and status == READY_STATUS,
        "training_split_manifest_roots_written": final_passed and status == READY_STATUS,
        "provenance_report_written": final_passed and status == READY_STATUS,
        "input_materialization_execution_authorized_next": False,
        "materialization_execution_authorized_next": False,
        "training_execution_authorized_next": False,
        "replay_execution_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    return report


def _output_summary(output_dir: Path) -> dict[str, Any]:
    return {
        "output_dir": str(output_dir),
        "candidate_member_source_manifest_json": str(output_dir / OUTPUT_FILES[0]),
        "training_split_manifest_roots_json": str(output_dir / OUTPUT_FILES[1]),
        "provenance_report_json": str(output_dir / OUTPUT_FILES[2]),
        "sha256sums": str(output_dir / SHA256SUMS_NAME),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_stable(payload), indent=2) + "\n", encoding="utf-8")


def _write_sha256sums(output_dir: Path, file_names: tuple[str, ...]) -> None:
    lines = []
    for name in file_names:
        path = output_dir / name
        lines.append(f"{_sha256(path)}  {name}")
    (output_dir / SHA256SUMS_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _load_json_dict(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [str(value)] if str(value) else []


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "actual": actual,
        "expected": expected,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _is_git_sha(value: str) -> bool:
    return bool(__import__("re").fullmatch(r"[0-9a-f]{40}", value or ""))


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
