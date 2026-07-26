from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camp_core", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2 import (  # noqa: E402
    AUTHORITY_SHA256,
    EXACT_DIRS,
    FIXED_DP_HEAD,
)
from scripts.integrations._diffusion_planner_v25_industrial_artifact_common import (  # noqa: E402
    git_head,
    object_from,
    write_atomic,
)


CURRENT = ROOT / "docs" / "diffusion_planner_current_status.md"
AUDIT = ROOT / "docs" / "diffusion_planner_v25_iteration_audit.md"
REPORT = (
    ROOT
    / "docs"
    / "diffusion_planner_v25_industrial_v3_multiroute_v2_report.md"
)
INDEX = (
    ROOT
    / "docs"
    / "diffusion_planner_v25_industrial_v3_multiroute_v2_evidence_index.md"
)
CURRENT_HEADING = (
    "## Current V25 Status - Industrial-v3 Project-authored Multiroute-v2 "
    "Development Execution and Evaluation Independently Reviewed"
)
AUDIT_HEADING = (
    "## V25 Industrial-v3 Project-authored Multiroute-v2 Development "
    "Execution and Evaluation Review"
)
ALLOWED_TRACKED_DRAFTS = {
    "scripts/integrations/materialize_diffusion_planner_v25_batch8_training_support_reference.py",
    "scripts/integrations/review_diffusion_planner_v25_batch8_training_support_reference.py",
}
EXPECTED_STATUSES = {
    "contract": "sealed_outcome_independent_multiroute_v2_contract",
    "contract_review": "independent_literal_contract_review_passed",
    "hardening_matrix": "sealed_zero_model_pre_execution_hardening_matrix",
    "hardening_matrix_review": (
        "independent_literal_hardening_matrix_review_passed"
    ),
    "hardening_focused": (
        "passed_zero_model_pre_execution_hardening_focused"
    ),
    "preflight": "passed_before_first_model_call",
    "preflight_review": (
        "independent_preflight_review_passed_before_first_model_call"
    ),
    "execution": "complete_full_denominator_hard_integrity_passed",
    "execution_review": "independent_raw_execution_review_passed",
    "evaluation": "sealed_exploratory_multiroute_industrial_v3_vector",
    "evaluation_review": "independent_literal_evaluation_review_passed",
}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    payload = (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _load_package(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError("final package must be an object")
    if value.get("authority_sha256") != AUTHORITY_SHA256:
        raise ValueError("final package authority drifted")
    artifacts = value.get("artifacts")
    if type(artifacts) is not dict or set(artifacts) != set(EXPECTED_STATUSES):
        raise ValueError("final package artifact role set drifted")
    for role, item in artifacts.items():
        if (
            type(item) is not dict
            or item.get("path") != EXACT_DIRS[role]
            or type(item.get("root_sha256")) is not str
            or len(item["root_sha256"]) != 64
        ):
            raise ValueError(f"final package artifact binding drifted: {role}")
    return value


def _machine_lines(section: str) -> list[str]:
    return [
        line
        for line in section.splitlines()
        if re.fullmatch(r"[a-z][a-z0-9_]*=[^\r\n]*", line)
    ]


def _write_docs(package: Mapping[str, Any]) -> dict[str, Any]:
    execution = package["execution_summary"]
    evaluation = package["evaluation_summary"]
    focused = package["focused_summary"]
    artifacts = package["artifacts"]
    if (
        execution.get("planned_tick_slots") != 19_200
        or execution.get("formal_model_calls") != 19_200
        or execution.get("hard_integrity_failure_count") != 0
        or execution.get("candidate_tensor_mutation_count") != 0
        or evaluation.get("scalar_leaf_count") != 161
        or evaluation.get("independent_cluster_count") != 100
        or focused.get("test_count", 0) <= 0
    ):
        raise ValueError("final package denominator or integrity summary drifted")
    availability = evaluation["availability_counts"]
    report_text = f"""# V25 Industrial-v3 Project-authored Multiroute-v2 Development Report

## Outcome

The single authorized development/nonholdout attempt completed the frozen
100-cluster, three-arm, 19,200-tick denominator.  Every attempted tick used one
same-ego single-invocation B=8 pool. Candidate0 selected row0; Static14D and
Scene14D consumed only their own arm/tick immutable pool. Sequential calls and
post-pool model/DP/latent/candidate-generation calls remained zero.

This is bounded development evidence. It is not Fresh or holdout evidence and
does not authorize a benefit, training-support, no-retraining, industrial
safety, ISO/SAE, real-road, production, promotion or deployment claim.

## Execution

- clusters: 100
- arms: 300
- planned/completed-or-typed-failed tick slots: 19,200
- formal same-ego B=8 model calls: 19,200
- Static14D selector calls: 6,400
- Scene14D selector calls: 6,400
- sequential calls: 0
- post-pool generation calls: 0
- tensor mutations: 0
- hard-integrity failures: 0

All failures, if any, remain in the full denominator; no drop, replacement,
complete-case substitution or rerun was used.

## Industrial-v3 evaluation

The accepted 56-parent/161-scalar-leaf vector was evaluated cluster-first.
Availability was:

- computed exploratory multiroute leaves: {availability['computed_exploratory_multiroute']}
- evidence-missing or mixed-applicability leaves: {availability['evidence_missing_or_mixed_applicability']}
- scientifically inapplicable leaves: {availability['scientifically_inapplicable']}

For each directed scalar with complete evidence, the report retains 100 paired
cluster deltas, exact-zero better/tie/worse counts and an ordinary two-sided
paired Student-t CI95. Ordinary intervals are descriptive, not familywise
claim evidence. Numeric NI/guardrail margins remain unauthorized, so Holm/IUT
and benefit claim gates remain not evaluable. No weighted total or SafetyCost
was computed.

## Preserved boundaries

The earlier sealed-inventory 0/100 result remains an immutable source-capacity
diagnostic. The project-authored source contract/materialization and this
continuation are additive. Fresh B2/B3/B4 identities, old artifacts, CAS,
fixed-DP source/checkpoint, selector weights/Theta, atoms/scales and claim rules
were not modified or reread for outcome values.
"""
    REPORT.write_text(report_text, encoding="utf-8")
    index_lines = [
        "# V25 Industrial-v3 Project-authored Multiroute-v2 Evidence Index",
        "",
        "| Role | Exact path | Root SHA256 |",
        "|---|---|---|",
    ]
    for role in EXPECTED_STATUSES:
        item = artifacts[role]
        index_lines.append(
            f"| `{role}` | `{item['path']}` | `{item['root_sha256']}` |"
        )
    index_lines.extend(
        [
            "",
            "The source-stage contract/materialization/reviews and continuation "
            "roots are bound inside the multiroute-v2 contract artifact.",
            "",
            "No Fresh/B4 outcome, SafetyCost, weighted total, training, "
            "retraining, promotion or deployment authority is present.",
        ]
    )
    INDEX.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    report_sha = _sha(REPORT)
    index_sha = _sha(INDEX)
    additions = {
        "current_v25_status": (
            "industrial_v3_project_authored_multiroute_v2_full_denominator_"
            "independently_reviewed_high_incremental_review_required"
        ),
        "current_v25_phase": (
            "development_nonholdout_100_cluster_compute_matched_closed_loop_"
            "descriptive_industrial_v3_vector"
        ),
        "current_v25_multiroute_v2_authority_sha256": AUTHORITY_SHA256,
        "current_v25_multiroute_v2_continuation_sha256": (
            "89e716d0fd13acea517853f93a67b1ab68abe312ae4815f2a4b8c678c0ec3a13"
        ),
        "current_v25_multiroute_v2_implementation_head": package[
            "implementation_head"
        ],
        "current_v25_multiroute_v2_fixed_dp_head": FIXED_DP_HEAD,
        "current_v25_multiroute_v2_cluster_count": "100",
        "current_v25_multiroute_v2_arm_count": "300",
        "current_v25_multiroute_v2_planned_tick_count": "19200",
        "current_v25_multiroute_v2_complete_tick_count": str(
            execution["terminal_accounting"]["complete"]
        ),
        "current_v25_multiroute_v2_failed_tick_count": str(
            execution["terminal_accounting"]["failed"]
        ),
        "current_v25_multiroute_v2_unattempted_tick_count": str(
            execution["terminal_accounting"]["unattempted"]
        ),
        "current_v25_multiroute_v2_formal_model_call_count": "19200",
        "current_v25_multiroute_v2_static_selector_call_count": "6400",
        "current_v25_multiroute_v2_scene_selector_call_count": "6400",
        "current_v25_multiroute_v2_sequential_call_count": "0",
        "current_v25_multiroute_v2_post_pool_generation_call_count": "0",
        "current_v25_multiroute_v2_tensor_mutation_count": "0",
        "current_v25_multiroute_v2_hard_integrity_failure_count": "0",
        "current_v25_multiroute_v2_parent_endpoint_count": "56",
        "current_v25_multiroute_v2_scalar_leaf_count": "161",
        "current_v25_multiroute_v2_computed_leaf_count": str(
            availability["computed_exploratory_multiroute"]
        ),
        "current_v25_multiroute_v2_missing_or_mixed_leaf_count": str(
            availability["evidence_missing_or_mixed_applicability"]
        ),
        "current_v25_multiroute_v2_inapplicable_leaf_count": str(
            availability["scientifically_inapplicable"]
        ),
        "current_v25_multiroute_v2_independent_cluster_count": "100",
        "current_v25_multiroute_v2_weighted_total_present": "false",
        "current_v25_multiroute_v2_legacy_safetycost_computed": "false",
        "current_v25_multiroute_v2_claim_authorized": "false",
        "current_v25_multiroute_v2_fresh_or_b4_outcome_values_read": "false",
        "current_v25_multiroute_v2_old_artifact_or_cas_write_count": "0",
        "current_v25_multiroute_v2_focused_test_count": str(
            focused["test_count"]
        ),
        "current_v25_multiroute_v2_report": REPORT.relative_to(ROOT).as_posix(),
        "current_v25_multiroute_v2_report_sha256": report_sha,
        "current_v25_multiroute_v2_evidence_index": INDEX.relative_to(
            ROOT
        ).as_posix(),
        "current_v25_multiroute_v2_evidence_index_sha256": index_sha,
        "next_work_target": (
            "high_incremental_review_of_industrial_v3_multiroute_v2_package"
        ),
    }
    for role, item in artifacts.items():
        additions[
            f"current_v25_multiroute_v2_{role}_root_sha256"
        ] = item["root_sha256"]
    current = CURRENT.read_text(encoding="utf-8")
    old_start = current.index("## Current V25 Status")
    old_end = current.index("\n## ", old_start + 3)
    old_lines = _machine_lines(current[old_start:old_end])
    order = [line.split("=", 1)[0] for line in old_lines]
    values = dict(line.split("=", 1) for line in old_lines)
    for key, value in additions.items():
        if key not in values:
            order.append(key)
        values[key] = str(value)
    machine = "\n".join(f"{key}={values[key]}" for key in order)
    prose = f"""{CURRENT_HEADING}
Reader contract: this named section is the only current V25 pointer source in
this file. Its machine tuple must match the EOF tuple in
`docs/diffusion_planner_v25_iteration_audit.md` field for field.

The authorized project-authored development/nonholdout multiroute-v2 chain
formed the complete 100-cluster, 300-arm and 19,200-tick denominator. The
execution and evaluation were independently reconstructed. The industrial-v3
result remains an endpoint vector with typed missingness; no weighted total,
SafetyCost gate, Fresh benefit or industrial claim was created.

High must perform the next incremental review. No further model, Fresh,
training, retraining, closed-loop, promotion or deployment action is
authorized by this pointer.

"""
    CURRENT.write_text(
        current[:old_start] + prose + machine + "\n" + current[old_end:],
        encoding="utf-8",
    )
    audit = AUDIT.read_text(encoding="utf-8").rstrip()
    if AUDIT_HEADING in audit:
        audit = audit.split(AUDIT_HEADING, 1)[0].rstrip()
    audit += (
        "\n\n"
        + AUDIT_HEADING
        + "\n\nThis EOF tuple records the independently reviewed, bounded "
        "development/nonholdout multiroute-v2 chain and creates no Fresh, "
        "benefit, training, industrial-safety or deployment authority.\n\n"
        + machine
        + "\n"
    )
    AUDIT.write_text(audit, encoding="utf-8")
    return {
        "pointer_field_count": len(order),
        "report_sha256": report_sha,
        "evidence_index_sha256": index_sha,
        "machine_tuple_sha256": _canonical_sha(values),
    }


def _verify_final_inputs(
    package: Mapping[str, Any],
    *,
    pointer_head: str,
    pointer_field_count: int,
) -> dict[str, Any]:
    if Path(sys.executable).as_posix() != "/root/autodl-tmp/dp312_venv/bin/python":
        raise ValueError("final docs must use frozen AutoDL interpreter")
    if sys.version_info < (3, 10):
        raise ValueError("final docs interpreter is too old")
    if git_head() != pointer_head:
        raise ValueError("final docs pointer HEAD drifted")
    origin = subprocess.run(
        ["git", "rev-parse", "origin/main"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    tracked = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    if origin != pointer_head:
        raise ValueError("final docs origin pointer drifted")
    if tracked:
        actual = {line[3:].replace("\\", "/") for line in tracked}
        if not actual.issubset(ALLOWED_TRACKED_DRAFTS):
            raise ValueError("final docs tracked scope drifted")
    artifacts = {}
    for role, expected_status in EXPECTED_STATUSES.items():
        item = package["artifacts"][role]
        path = Path(item["path"])
        root = item["root_sha256"]
        verify_complete_seal(path, root, label=f"multiroute-v2 final {role}")
        report = object_from(path / "report.json")
        if report.get("status") != expected_status:
            raise ValueError(f"final docs artifact status drifted: {role}")
        artifacts[role] = report
    execution = artifacts["execution"]
    evaluation = artifacts["evaluation"]
    evaluation_review = artifacts["evaluation_review"]
    if (
        execution.get("planned_tick_slots") != 19_200
        or execution.get("formal_model_calls") != 19_200
        or execution.get("terminal_accounting", {}).get("unattempted") != 0
        or execution.get("hard_integrity_failure_count") != 0
        or evaluation.get("scalar_leaf_count") != 161
        or evaluation.get("independent_cluster_count") != 100
        or evaluation_review.get("cluster_leaf_arm_values_rebuilt")
        != 100 * 161 * 3
        or evaluation.get("weighted_total_present") is not False
        or evaluation.get("claim_authorized") is not False
    ):
        raise ValueError("final docs scientific boundary drifted")
    current = CURRENT.read_text(encoding="utf-8")
    audit = AUDIT.read_text(encoding="utf-8")
    current_section = current.split(CURRENT_HEADING, 1)[1].split("\n## ", 1)[0]
    audit_section = audit.split(AUDIT_HEADING, 1)[1]
    current_lines = _machine_lines(current_section)
    audit_lines = _machine_lines(audit_section)
    if (
        current_lines != audit_lines
        or len(current_lines) != pointer_field_count
        or len(set(line.split("=", 1)[0] for line in current_lines))
        != pointer_field_count
    ):
        raise ValueError("final docs Current/audit tuple drifted")
    values = dict(line.split("=", 1) for line in current_lines)
    if (
        values["current_v25_multiroute_v2_report_sha256"] != _sha(REPORT)
        or values["current_v25_multiroute_v2_evidence_index_sha256"]
        != _sha(INDEX)
    ):
        raise ValueError("final docs report/index SHA drifted")
    dp_repo = Path("/root/autodl-tmp/Diffusion-Planner")
    dp_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=dp_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dp_dirty = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        cwd=dp_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if dp_head != FIXED_DP_HEAD or dp_dirty:
        raise ValueError("final docs fixed-DP authority drifted")
    return {
        "artifacts": artifacts,
        "pointer_values": values,
        "report_sha256": _sha(REPORT),
        "evidence_index_sha256": _sha(INDEX),
    }


def seal_final(
    output: Path,
    *,
    package: Mapping[str, Any],
    pointer_head: str,
    pointer_field_count: int,
) -> str:
    if output.resolve() != Path(EXACT_DIRS["final_docs"]):
        raise ValueError("multiroute-v2 final docs exact dir drifted")
    verified = _verify_final_inputs(
        package,
        pointer_head=pointer_head,
        pointer_field_count=pointer_field_count,
    )
    report = {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_final_docs_v1"
        ),
        "status": "sealed_complete_multiroute_v2_final_package",
        "authority_sha256": AUTHORITY_SHA256,
        "implementation_head": package["implementation_head"],
        "pointer_head": pointer_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "artifact_roots": {
            role: item["root_sha256"]
            for role, item in package["artifacts"].items()
        },
        "pointer_field_count": pointer_field_count,
        "current_audit_exact": True,
        "report_sha256": verified["report_sha256"],
        "evidence_index_sha256": verified["evidence_index_sha256"],
        "cluster_count": 100,
        "arm_count": 300,
        "planned_tick_count": 19_200,
        "formal_model_call_count": 19_200,
        "sequential_call_count": 0,
        "post_pool_generation_call_count": 0,
        "scalar_leaf_count": 161,
        "weighted_total_present": False,
        "legacy_safetycost_computed": False,
        "fresh_or_b4_outcome_values_read": False,
        "old_artifact_or_cas_writes": 0,
        "claim_authorized": False,
        "interpreter": {
            "sys_executable": sys.executable,
            "version_info": list(sys.version_info[:3]),
            "sys_prefix": sys.prefix,
        },
    }
    return write_atomic(
        output,
        report,
        {
            "role": "industrial_v3_multiroute_v2_final_docs",
            "authority_sha256": AUTHORITY_SHA256,
            "implementation_head": package["implementation_head"],
            "pointer_head": pointer_head,
            "execution_root_sha256": package["artifacts"]["execution"][
                "root_sha256"
            ],
            "evaluation_root_sha256": package["artifacts"]["evaluation"][
                "root_sha256"
            ],
        },
        label="V25 industrial-v3 multiroute-v2 final docs",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    docs = sub.add_parser("write-docs")
    docs.add_argument("--package", type=Path, required=True)
    final = sub.add_parser("seal-final")
    final.add_argument("--output", type=Path, required=True)
    final.add_argument("--package", type=Path, required=True)
    final.add_argument("--pointer-head", required=True)
    final.add_argument("--pointer-field-count", type=int, required=True)
    args = parser.parse_args()
    package = _load_package(args.package)
    if args.command == "write-docs":
        if git_head() != package["implementation_head"]:
            raise ValueError("docs writer implementation HEAD drifted")
        result = _write_docs(package)
        print(json.dumps(result, sort_keys=True))
    else:
        root = seal_final(
            args.output,
            package=package,
            pointer_head=args.pointer_head,
            pointer_field_count=args.pointer_field_count,
        )
        print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
