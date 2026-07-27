from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


AUTHORITY_SHA256 = (
    "64b65e2cf3d8e19863d298392051cb9f9926e47a175330bc4bbc63f153f24531"
)
PARENT_AUTHORITY_SHA256 = (
    "c065e1b08e711a6cdeb84c14f94d5941019f613562ac452c028e8f903b537866"
)
BASE_HEAD = "8fc8e271e311c320514940ab4bf8950284a6e98f"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXECUTION_ROOT_SHA256 = (
    "7d143a95cf42aa702e362dd75a1b8c5d7559690bdcd701a001ee0fac186fb052"
)
EXECUTION_REVIEW_ROOT_SHA256 = (
    "6c90f5e966e78203702c71168098ae3fe93f385e7af750890e248ef156cabf27"
)
SUPERSEDED_EVALUATION_ROOT_SHA256 = (
    "2cf2689fddabb07f583f51e512ca21a867b31bd245117e3c071aa178e3f531b5"
)
INDUSTRIAL_CONTRACT_ROOT_SHA256 = (
    "908fe1d57014e4932f71462d6d7e73ec58390f3296b3018df38092e4c0b128cb"
)
INDUSTRIAL_CONTRACT_REVIEW_ROOT_SHA256 = (
    "23bb07ac537f9d53f7a2860b2314f55da4e2d468590d002c6cf25733f5e48556"
)
INDUSTRIAL_CAPABILITY_ROOT_SHA256 = (
    "fbcc8ab194520534c3b4986cccaf3d9a073b2cf975b6e3f006f61abe7791f20d"
)
INDUSTRIAL_CAPABILITY_REVIEW_ROOT_SHA256 = (
    "f32cb19b2c7bbd64e290f07a270f3e43462d31c86dc130a0c23a8b6eb363eec3"
)
AFFECTED_LEAF_SET_SHA256 = (
    "7d0a406b00ce2b7b86cce50f89d6cfa24714c37493100278b55bcb567efb33af"
)
ARMS = ("pool_matched_candidate0", "Static14D", "Scene14D")
TICKS_PER_ARM = 64
CLUSTER_COUNT = 100
ACTOR_FIELDS = (
    "id",
    "position_xy",
    "velocity_xy_mps",
    "heading_rad",
    "length_m",
    "width_m",
    "wheelbase_m",
)
LEGACY_SUPPLEMENTARY_HEADER_FIELDS = (
    "spawn_config_sha256",
    "initial_state_sha256",
    "initial_input_sha256",
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


def affected_leaf_ids() -> tuple[str, ...]:
    ids = [
        "safety.collision_any",
        "safety.collision_episode_count",
        "safety.collision_duration_s",
        "safety.min_full_polygon_clearance_m",
        "safety.max_closing_speed_mps",
        "safety.min_geometry_ttc_s",
        "safety.max_drac_mps2",
    ]
    grids = (
        ("clearance_m", "le", "m", ("0", "0p5", "1", "2")),
        ("ttc_s", "le", "s", ("0p5", "1", "2", "3", "5")),
        ("closing_mps", "ge", "mps", ("0p5", "1", "2", "5")),
        ("drac_mps2", "ge", "mps2", ("0p5", "1", "2", "3", "5")),
    )
    for family, comparator, unit, tokens in grids:
        for token in tokens:
            ids.extend(
                (
                    f"safety.{family}_{comparator}_{token}{unit}_duration_s",
                    f"safety.{family}_{comparator}_{token}{unit}_episode_count",
                )
            )
    value = tuple(ids)
    if len(value) != 43 or canonical_sha256(value) != AFFECTED_LEAF_SET_SHA256:
        raise ValueError("affected 43-leaf registry drifted")
    return value


def exact_dirs(implementation_head: str, continuation_sha256: str) -> dict[str, str]:
    if len(implementation_head) != 40 or len(continuation_sha256) != 64:
        raise ValueError("implementation or continuation SHA is invalid")
    prefix = (
        "/root/autodl-tmp/"
        "camp_dp_v25_industrial_v3_multiroute_v2_"
        "evaluation_actor_binding_replacement_"
        f"{implementation_head[:8]}_{continuation_sha256[:8]}_"
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


def continuation_preimage(implementation_head: str) -> dict[str, Any]:
    return {
        "authority_sha256": AUTHORITY_SHA256,
        "implementation_head": implementation_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "execution_root": EXECUTION_ROOT_SHA256,
        "execution_review_root": EXECUTION_REVIEW_ROOT_SHA256,
        "superseded_evaluation_root": SUPERSEDED_EVALUATION_ROOT_SHA256,
        "affected_leaf_set_sha256": AFFECTED_LEAF_SET_SHA256,
        "industrial_contract_root": INDUSTRIAL_CONTRACT_ROOT_SHA256,
        "industrial_contract_review_root": INDUSTRIAL_CONTRACT_REVIEW_ROOT_SHA256,
        "industrial_capability_root": INDUSTRIAL_CAPABILITY_ROOT_SHA256,
        "industrial_capability_review_root": (
            INDUSTRIAL_CAPABILITY_REVIEW_ROOT_SHA256
        ),
    }


def continuation_sha256(implementation_head: str) -> str:
    return canonical_sha256(continuation_preimage(implementation_head))


def _finite_scalar(value: Any, label: str) -> float:
    if (
        type(value) not in {int, float}
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"{label} must be a finite scalar")
    return float(value)


def _finite_vector(value: Any, size: int, label: str) -> list[float]:
    if type(value) is not list or len(value) != size:
        raise ValueError(f"{label} shape drifted")
    return [_finite_scalar(item, label) for item in value]


def validate_sealed_actor_binding(
    arm: Mapping[str, Any],
    *,
    execution_root_sha256: str,
    cluster_root_sha256: str,
    cluster_index: int,
    expected_arm: str,
) -> dict[str, Any]:
    if execution_root_sha256 != EXECUTION_ROOT_SHA256:
        raise ValueError("sealed actor execution-root binding drifted")
    if (
        expected_arm not in ARMS
        or arm.get("arm") != expected_arm
        or type(cluster_index) is not int
        or not 0 <= cluster_index < CLUSTER_COUNT
        or type(cluster_root_sha256) is not str
        or len(cluster_root_sha256) != 64
    ):
        raise ValueError("sealed actor cluster or arm binding drifted")
    ticks = arm.get("ticks")
    if type(ticks) is not list or len(ticks) != TICKS_PER_ARM:
        raise ValueError("sealed actor tick denominator drifted")
    receipts = []
    expected_actor_ids: tuple[str, ...] | None = None
    for tick_index, tick in enumerate(ticks):
        if type(tick) is not dict or tick.get("tick_index") != tick_index:
            raise ValueError("sealed actor tick binding drifted")
        safety = tick.get("_safety_record")
        actors = safety.get("actors") if type(safety) is dict else None
        if type(actors) is not list:
            raise ValueError("sealed actor stream is unproven")
        normalized = []
        ids = []
        for actor in actors:
            if type(actor) is not dict or set(actor) != set(ACTOR_FIELDS):
                raise ValueError("sealed actor field set drifted")
            actor_id = str(actor["id"])
            ids.append(actor_id)
            row = {
                "id": actor_id,
                "position_xy": _finite_vector(
                    actor["position_xy"], 2, "actor position_xy"
                ),
                "velocity_xy_mps": _finite_vector(
                    actor["velocity_xy_mps"], 2, "actor velocity_xy_mps"
                ),
                "heading_rad": _finite_scalar(
                    actor["heading_rad"], "actor heading_rad"
                ),
                "length_m": _finite_scalar(actor["length_m"], "actor length_m"),
                "width_m": _finite_scalar(actor["width_m"], "actor width_m"),
                "wheelbase_m": _finite_scalar(
                    actor["wheelbase_m"], "actor wheelbase_m"
                ),
            }
            if (
                row["length_m"] <= 0.0
                or row["width_m"] <= 0.0
                or row["wheelbase_m"] <= 0.0
            ):
                raise ValueError("sealed actor dimensions must be positive")
            normalized.append(row)
        if len(ids) != len(set(ids)) or ids != sorted(ids):
            raise ValueError("sealed actor IDs must be unique and sorted")
        actor_ids = tuple(ids)
        if expected_actor_ids is None:
            expected_actor_ids = actor_ids
        elif actor_ids != expected_actor_ids:
            raise ValueError("sealed actor identity set drifted across ticks")
        receipts.append(
            {
                "execution_root_sha256": execution_root_sha256,
                "cluster_root_sha256": cluster_root_sha256,
                "cluster_index": cluster_index,
                "arm": expected_arm,
                "tick_index": tick_index,
                "actor_count": len(normalized),
                "actor_state_sha256": canonical_sha256(normalized),
            }
        )
    return {
        "schema_version": "camp_dp_v25_multiroute_sealed_actor_binding_v1",
        "execution_root_sha256": execution_root_sha256,
        "cluster_root_sha256": cluster_root_sha256,
        "cluster_index": cluster_index,
        "arm": expected_arm,
        "tick_count": TICKS_PER_ARM,
        "actor_ids": list(expected_actor_ids or ()),
        "actor_count_per_tick": [row["actor_count"] for row in receipts],
        "tick_receipts": receipts,
        "binding_sha256": canonical_sha256(receipts),
        "legacy_supplementary_header_gate_used": False,
        "candidate0_special_case_used": False,
    }


def correction_contract(
    implementation_head: str,
    *,
    continuation: str | None = None,
) -> dict[str, Any]:
    continuation = continuation or continuation_sha256(implementation_head)
    leaves = affected_leaf_ids()
    return {
        "schema_version": (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "evaluation_actor_binding_correction_contract_v1"
        ),
        "authority_sha256": AUTHORITY_SHA256,
        "parent_authority_sha256": PARENT_AUTHORITY_SHA256,
        "implementation_head": implementation_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "continuation_preimage": continuation_preimage(implementation_head),
        "continuation_sha256": continuation,
        "exact_dirs": exact_dirs(implementation_head, continuation),
        "scientific_inputs": {
            "execution_root_sha256": EXECUTION_ROOT_SHA256,
            "execution_review_root_sha256": EXECUTION_REVIEW_ROOT_SHA256,
            "model_execution_rerun": False,
        },
        "superseded_evaluation": {
            "root_sha256": SUPERSEDED_EVALUATION_ROOT_SHA256,
            "accepted_scientific_result": False,
            "used_as_corrected_result_input": False,
            "role": "unreviewed_engineering_diagnostic_only",
        },
        "affected_leaf_ids": list(leaves),
        "affected_leaf_count": len(leaves),
        "affected_leaf_set_sha256": AFFECTED_LEAF_SET_SHA256,
        "unaffected_leaf_count": 118,
        "binding": {
            "name": "multiroute_sealed_actor_binding",
            "source": (
                "sealed execution/cluster/arm/tick/_safety_record/actors"
            ),
            "required_actor_fields": list(ACTOR_FIELDS),
            "units": {
                "position_xy": "m",
                "velocity_xy_mps": "m/s",
                "heading_rad": "rad",
                "length_m": "m",
                "width_m": "m",
                "wheelbase_m": "m",
            },
            "three_arm_identical_qualification_rule": True,
            "candidate0_special_case_allowed": False,
            "legacy_supplementary_header_gate_allowed": False,
        },
        "unaffected_regression": (
            "all_118_leaf_semantics_and_values_recomputed_from_execution_"
            "and_exactly_equal_to_superseded_diagnostic"
        ),
        "collision_onset_proxy_change_allowed": False,
        "model_dp_pool_selector_execution_calls": 0,
        "fresh_or_holdout": False,
        "claim_authorized": False,
        "five_class_flow_policy": True,
    }


__all__ = [
    "ACTOR_FIELDS",
    "AFFECTED_LEAF_SET_SHA256",
    "ARMS",
    "AUTHORITY_SHA256",
    "BASE_HEAD",
    "CLUSTER_COUNT",
    "EXECUTION_REVIEW_ROOT_SHA256",
    "EXECUTION_ROOT_SHA256",
    "FIXED_DP_HEAD",
    "INDUSTRIAL_CAPABILITY_REVIEW_ROOT_SHA256",
    "INDUSTRIAL_CAPABILITY_ROOT_SHA256",
    "INDUSTRIAL_CONTRACT_REVIEW_ROOT_SHA256",
    "INDUSTRIAL_CONTRACT_ROOT_SHA256",
    "LEGACY_SUPPLEMENTARY_HEADER_FIELDS",
    "PARENT_AUTHORITY_SHA256",
    "SUPERSEDED_EVALUATION_ROOT_SHA256",
    "TICKS_PER_ARM",
    "affected_leaf_ids",
    "canonical_bytes",
    "canonical_sha256",
    "continuation_preimage",
    "continuation_sha256",
    "correction_contract",
    "exact_dirs",
    "validate_sealed_actor_binding",
]
