from __future__ import annotations

import hashlib
import json
from typing import Any


AUTHORITY_SHA256 = (
    "181be7266035f4a1a40c11bf1bf1c3458dd79491e97e5e91ecd1914cbc7672b4"
)
BASE_HEAD = "495d3b2b65e88aa6050ac88559acf7832ea6c3cc"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CORRECTION_CONTINUATION = (
    "ca642a15dd612ef925ce6f6e5783597e9e0a41be49e1385cdf0143f5a966fc28"
)
PARENT_AUTHORITIES = (
    "c065e1b08e711a6cdeb84c14f94d5941019f613562ac452c028e8f903b537866",
    "64b65e2cf3d8e19863d298392051cb9f9926e47a175330bc4bbc63f153f24531",
)
EXECUTION_ROOT = (
    "7d143a95cf42aa702e362dd75a1b8c5d7559690bdcd701a001ee0fac186fb052"
)
EXECUTION_REVIEW_ROOT = (
    "6c90f5e966e78203702c71168098ae3fe93f385e7af750890e248ef156cabf27"
)
EVALUATION_ROOT = (
    "16a156ac21fba0cd5038802df7b0735f4c66d25b1cb73663fd8710fda97cdf8c"
)
PREFLIGHT_ROOT = (
    "5f56246ac312682920f0aaae63cab3d5f4f0ea5e75c85156b30395ce8e30f341"
)
INDUSTRIAL_CONTRACT_ROOT = (
    "908fe1d57014e4932f71462d6d7e73ec58390f3296b3018df38092e4c0b128cb"
)
INDUSTRIAL_CONTRACT_REVIEW_ROOT = (
    "23bb07ac537f9d53f7a2860b2314f55da4e2d468590d002c6cf25733f5e48556"
)
INDUSTRIAL_CAPABILITY_ROOT = (
    "fbcc8ab194520534c3b4986cccaf3d9a073b2cf975b6e3f006f61abe7791f20d"
)
INDUSTRIAL_CAPABILITY_REVIEW_ROOT = (
    "f32cb19b2c7bbd64e290f07a270f3e43462d31c86dc130a0c23a8b6eb363eec3"
)
AFFECTED_LEAF_SET_SHA256 = (
    "7d0a406b00ce2b7b86cce50f89d6cfa24714c37493100278b55bcb567efb33af"
)
SOURCE_ARTIFACTS = (
    (
        "failure_closeout",
        "6a4d763ad496cef16ec8229b599a0361aef628dcfe4df416eab73b8d332b2fcd",
        "camp_dp_v25_industrial_v3_multiroute_v2_evaluation_actor_binding_failure_closeout_v1",
        "attempt_stopped_engineering_recoverable",
    ),
    (
        "failure_closeout_review",
        "693efde930fe775853ecc80d8263b78f782ad95bfa72e89d99f2793184a2d363",
        "camp_dp_v25_industrial_v3_multiroute_v2_evaluation_actor_binding_failure_closeout_review_v1",
        "independent_failure_closeout_review_passed",
    ),
    (
        "correction_contract",
        "ceb57c315c6c729fb61b30ff9c7521db7c43af6ced278d1ca3ce929e1dfe9d87",
        "camp_dp_v25_industrial_v3_multiroute_v2_evaluation_actor_binding_correction_contract_artifact_v1",
        "outcome_independent_correction_contract_frozen",
    ),
    (
        "correction_contract_review",
        "fa597929a095459ac3cf95283134b3013f499920fe754eb0e97df2a9f06de5a8",
        "camp_dp_v25_industrial_v3_multiroute_v2_evaluation_actor_binding_correction_contract_review_v1",
        "independent_literal_correction_contract_review_passed",
    ),
    (
        "focused",
        "a0eb02bf9ca011cceedc310898b912692f83ffb1efc2ca8b880b10e5f4110653",
        "camp_dp_v25_industrial_v3_multiroute_v2_evaluation_actor_binding_focused_v1",
        "focused_tdd_passed",
    ),
)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def old_exact_dirs() -> dict[str, str]:
    prefix = (
        "/root/autodl-tmp/"
        "camp_dp_v25_industrial_v3_multiroute_v2_"
        "evaluation_actor_binding_replacement_495d3b2b_ca642a15_"
    )
    return {
        role: prefix + role
        for role in (
            "failure_closeout",
            "failure_closeout_review",
            "correction_contract",
            "correction_contract_review",
            "focused",
            "evaluation",
            "evaluation_review",
            "final_docs",
        )
    }


def exact_dirs(implementation_head: str) -> dict[str, str]:
    if (
        type(implementation_head) is not str
        or len(implementation_head) != 40
        or any(character not in "0123456789abcdef" for character in implementation_head)
    ):
        raise ValueError("implementation HEAD must be lowercase 40-hex")
    prefix = (
        "/root/autodl-tmp/"
        "camp_dp_v25_industrial_v3_multiroute_v2_"
        f"merged_review_recovery_{implementation_head[:8]}_181be726_"
    )
    return {
        role: prefix + role
        for role in (
            "stage_authority",
            "stage_authority_review",
            "stage_authority_operation",
            "orchestration_focused",
            "evaluation_review_operation",
            "evaluation_review",
            "final_docs",
        )
    }


def stage_authority_payload(
    implementation_head: str,
    source_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "merged_review_recovery_stage_authority_v1"
        ),
        "status": "complete_external_authority_chain_frozen",
        "authority_sha256": AUTHORITY_SHA256,
        "parent_authorities": list(PARENT_AUTHORITIES),
        "base_head": BASE_HEAD,
        "implementation_head": implementation_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "correction_continuation": CORRECTION_CONTINUATION,
        "exact_dirs": exact_dirs(implementation_head),
        "source_artifacts": source_artifacts,
        "preflight_root_sha256": PREFLIGHT_ROOT,
        "industrial_contract_root_sha256": INDUSTRIAL_CONTRACT_ROOT,
        "industrial_contract_review_root_sha256": (
            INDUSTRIAL_CONTRACT_REVIEW_ROOT
        ),
        "industrial_capability_root_sha256": INDUSTRIAL_CAPABILITY_ROOT,
        "industrial_capability_review_root_sha256": (
            INDUSTRIAL_CAPABILITY_REVIEW_ROOT
        ),
        "execution_root_sha256": EXECUTION_ROOT,
        "execution_review_root_sha256": EXECUTION_REVIEW_ROOT,
        "evaluation_root_sha256": EVALUATION_ROOT,
        "affected_leaf_set_sha256": AFFECTED_LEAF_SET_SHA256,
        "frozen_denominator": {
            "clusters": 100,
            "arms": 300,
            "ticks": 19_200,
        },
        "producer_evaluator_model_execution_rerun": False,
        "fresh_or_holdout_outcome_read": False,
        "claim_authorized": False,
        "five_class_flow_policy": True,
    }


__all__ = [
    "AFFECTED_LEAF_SET_SHA256",
    "AUTHORITY_SHA256",
    "BASE_HEAD",
    "CORRECTION_CONTINUATION",
    "EVALUATION_ROOT",
    "EXECUTION_REVIEW_ROOT",
    "EXECUTION_ROOT",
    "FIXED_DP_HEAD",
    "INDUSTRIAL_CAPABILITY_REVIEW_ROOT",
    "INDUSTRIAL_CAPABILITY_ROOT",
    "INDUSTRIAL_CONTRACT_REVIEW_ROOT",
    "INDUSTRIAL_CONTRACT_ROOT",
    "PARENT_AUTHORITIES",
    "PREFLIGHT_ROOT",
    "SOURCE_ARTIFACTS",
    "canonical_bytes",
    "canonical_sha256",
    "exact_dirs",
    "old_exact_dirs",
    "stage_authority_payload",
]
