from __future__ import annotations

from typing import Any, Mapping


EXPECTED_AUTHORITY = (
    "181be7266035f4a1a40c11bf1bf1c3458dd79491e97e5e91ecd1914cbc7672b4"
)
EXPECTED_BASE_HEAD = "495d3b2b65e88aa6050ac88559acf7832ea6c3cc"
EXPECTED_FIXED_DP = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_CONTINUATION = (
    "ca642a15dd612ef925ce6f6e5783597e9e0a41be49e1385cdf0143f5a966fc28"
)
EXPECTED_PARENT_AUTHORITIES = [
    "c065e1b08e711a6cdeb84c14f94d5941019f613562ac452c028e8f903b537866",
    "64b65e2cf3d8e19863d298392051cb9f9926e47a175330bc4bbc63f153f24531",
]
EXPECTED_PREFLIGHT_ROOT = (
    "5f56246ac312682920f0aaae63cab3d5f4f0ea5e75c85156b30395ce8e30f341"
)
EXPECTED_EXECUTION_ROOT = (
    "7d143a95cf42aa702e362dd75a1b8c5d7559690bdcd701a001ee0fac186fb052"
)
EXPECTED_EXECUTION_REVIEW_ROOT = (
    "6c90f5e966e78203702c71168098ae3fe93f385e7af750890e248ef156cabf27"
)
EXPECTED_EVALUATION_ROOT = (
    "16a156ac21fba0cd5038802df7b0735f4c66d25b1cb73663fd8710fda97cdf8c"
)
EXPECTED_AFFECTED_LEAF_SET = (
    "7d0a406b00ce2b7b86cce50f89d6cfa24714c37493100278b55bcb567efb33af"
)
EXPECTED_INDUSTRIAL_ROOTS = {
    "industrial_contract_root_sha256": (
        "908fe1d57014e4932f71462d6d7e73ec58390f3296b3018df38092e4c0b128cb"
    ),
    "industrial_contract_review_root_sha256": (
        "23bb07ac537f9d53f7a2860b2314f55da4e2d468590d002c6cf25733f5e48556"
    ),
    "industrial_capability_root_sha256": (
        "fbcc8ab194520534c3b4986cccaf3d9a073b2cf975b6e3f006f61abe7791f20d"
    ),
    "industrial_capability_review_root_sha256": (
        "f32cb19b2c7bbd64e290f07a270f3e43462d31c86dc130a0c23a8b6eb363eec3"
    ),
}
EXPECTED_SOURCE_ARTIFACTS = [
    {
        "role": "failure_closeout",
        "root_sha256": (
            "6a4d763ad496cef16ec8229b599a0361aef628dcfe4df416eab73b8d332b2fcd"
        ),
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "evaluation_actor_binding_failure_closeout_v1"
        ),
        "status": "attempt_stopped_engineering_recoverable",
    },
    {
        "role": "failure_closeout_review",
        "root_sha256": (
            "693efde930fe775853ecc80d8263b78f782ad95bfa72e89d99f2793184a2d363"
        ),
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "evaluation_actor_binding_failure_closeout_review_v1"
        ),
        "status": "independent_failure_closeout_review_passed",
    },
    {
        "role": "correction_contract",
        "root_sha256": (
            "ceb57c315c6c729fb61b30ff9c7521db7c43af6ced278d1ca3ce929e1dfe9d87"
        ),
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "evaluation_actor_binding_correction_contract_artifact_v1"
        ),
        "status": "outcome_independent_correction_contract_frozen",
    },
    {
        "role": "correction_contract_review",
        "root_sha256": (
            "fa597929a095459ac3cf95283134b3013f499920fe754eb0e97df2a9f06de5a8"
        ),
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "evaluation_actor_binding_correction_contract_review_v1"
        ),
        "status": "independent_literal_correction_contract_review_passed",
    },
    {
        "role": "focused",
        "root_sha256": (
            "a0eb02bf9ca011cceedc310898b912692f83ffb1efc2ca8b880b10e5f4110653"
        ),
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "evaluation_actor_binding_focused_v1"
        ),
        "status": "focused_tdd_passed",
    },
]


def _expected_dirs(implementation_head: str) -> dict[str, str]:
    if (
        type(implementation_head) is not str
        or len(implementation_head) != 40
        or any(character not in "0123456789abcdef" for character in implementation_head)
    ):
        raise ValueError("reviewer implementation HEAD is invalid")
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


def review_stage_authority_literal(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("stage authority must be an object")
    implementation_head = value.get("implementation_head")
    for key, expected in EXPECTED_INDUSTRIAL_ROOTS.items():
        if value.get(key) != expected:
            raise ValueError(f"stage authority industrial root drifted: {key}")
    if (
        value.get("schema_version")
        != (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "merged_review_recovery_stage_authority_v1"
        )
        or value.get("status") != "complete_external_authority_chain_frozen"
        or value.get("authority_sha256") != EXPECTED_AUTHORITY
        or value.get("parent_authorities") != EXPECTED_PARENT_AUTHORITIES
        or value.get("base_head") != EXPECTED_BASE_HEAD
        or value.get("fixed_dp_head") != EXPECTED_FIXED_DP
        or value.get("correction_continuation") != EXPECTED_CONTINUATION
        or value.get("exact_dirs") != _expected_dirs(implementation_head)
        or value.get("source_artifacts") != EXPECTED_SOURCE_ARTIFACTS
        or value.get("preflight_root_sha256") != EXPECTED_PREFLIGHT_ROOT
        or value.get("execution_root_sha256") != EXPECTED_EXECUTION_ROOT
        or value.get("execution_review_root_sha256")
        != EXPECTED_EXECUTION_REVIEW_ROOT
        or value.get("evaluation_root_sha256") != EXPECTED_EVALUATION_ROOT
        or value.get("affected_leaf_set_sha256")
        != EXPECTED_AFFECTED_LEAF_SET
        or value.get("frozen_denominator")
        != {"clusters": 100, "arms": 300, "ticks": 19_200}
        or value.get("producer_evaluator_model_execution_rerun") is not False
        or value.get("fresh_or_holdout_outcome_read") is not False
        or value.get("claim_authorized") is not False
        or value.get("five_class_flow_policy") is not True
    ):
        raise ValueError("stage authority semantics drifted")
    return dict(value)


__all__ = [
    "EXPECTED_AUTHORITY",
    "EXPECTED_EVALUATION_ROOT",
    "EXPECTED_EXECUTION_REVIEW_ROOT",
    "EXPECTED_EXECUTION_ROOT",
    "EXPECTED_PREFLIGHT_ROOT",
    "EXPECTED_SOURCE_ARTIFACTS",
    "review_stage_authority_literal",
]
