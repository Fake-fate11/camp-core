from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping


EXPECTED_AUTHORITY = (
    "64b65e2cf3d8e19863d298392051cb9f9926e47a175330bc4bbc63f153f24531"
)
EXPECTED_PARENT_AUTHORITY = (
    "c065e1b08e711a6cdeb84c14f94d5941019f613562ac452c028e8f903b537866"
)
EXPECTED_EXECUTION_ROOT = (
    "7d143a95cf42aa702e362dd75a1b8c5d7559690bdcd701a001ee0fac186fb052"
)
EXPECTED_EXECUTION_REVIEW_ROOT = (
    "6c90f5e966e78203702c71168098ae3fe93f385e7af750890e248ef156cabf27"
)
EXPECTED_SUPERSEDED_EVALUATION_ROOT = (
    "2cf2689fddabb07f583f51e512ca21a867b31bd245117e3c071aa178e3f531b5"
)
EXPECTED_AFFECTED_LEAF_SET_SHA = (
    "7d0a406b00ce2b7b86cce50f89d6cfa24714c37493100278b55bcb567efb33af"
)
EXPECTED_ARMS = ("pool_matched_candidate0", "Static14D", "Scene14D")
EXPECTED_ACTOR_FIELDS = (
    "id",
    "position_xy",
    "velocity_xy_mps",
    "heading_rad",
    "length_m",
    "width_m",
    "wheelbase_m",
)


def _canonical_bytes(value: Any) -> bytes:
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


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def expected_affected_leaf_ids() -> tuple[str, ...]:
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
    result = tuple(ids)
    if (
        len(result) != 43
        or _canonical_sha(result) != EXPECTED_AFFECTED_LEAF_SET_SHA
    ):
        raise ValueError("reviewer affected leaf literals drifted")
    return result


def review_contract_literal(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("reviewer contract must be an object")
    leaves = expected_affected_leaf_ids()
    binding = value.get("binding")
    scientific = value.get("scientific_inputs")
    superseded = value.get("superseded_evaluation")
    if (
        value.get("schema_version")
        != (
            "camp_dp_v25_industrial_v3_multiroute_v2_"
            "evaluation_actor_binding_correction_contract_v1"
        )
        or value.get("authority_sha256") != EXPECTED_AUTHORITY
        or value.get("parent_authority_sha256") != EXPECTED_PARENT_AUTHORITY
        or value.get("affected_leaf_ids") != list(leaves)
        or value.get("affected_leaf_count") != 43
        or value.get("affected_leaf_set_sha256")
        != EXPECTED_AFFECTED_LEAF_SET_SHA
        or value.get("unaffected_leaf_count") != 118
        or type(scientific) is not dict
        or scientific.get("execution_root_sha256") != EXPECTED_EXECUTION_ROOT
        or scientific.get("execution_review_root_sha256")
        != EXPECTED_EXECUTION_REVIEW_ROOT
        or scientific.get("model_execution_rerun") is not False
        or type(superseded) is not dict
        or superseded.get("root_sha256")
        != EXPECTED_SUPERSEDED_EVALUATION_ROOT
        or superseded.get("accepted_scientific_result") is not False
        or superseded.get("used_as_corrected_result_input") is not False
        or type(binding) is not dict
        or binding.get("name") != "multiroute_sealed_actor_binding"
        or binding.get("required_actor_fields") != list(EXPECTED_ACTOR_FIELDS)
        or binding.get("three_arm_identical_qualification_rule") is not True
        or binding.get("candidate0_special_case_allowed") is not False
        or binding.get("legacy_supplementary_header_gate_allowed") is not False
        or value.get("collision_onset_proxy_change_allowed") is not False
        or value.get("model_dp_pool_selector_execution_calls") != 0
        or value.get("fresh_or_holdout") is not False
        or value.get("claim_authorized") is not False
        or value.get("five_class_flow_policy") is not True
    ):
        raise ValueError("reviewer actor-binding contract semantics drifted")
    return dict(value)


def _number(value: Any, label: str) -> float:
    if (
        type(value) not in {int, float}
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"reviewer {label} must be finite")
    return float(value)


def _vector(value: Any, label: str) -> list[float]:
    if type(value) is not list or len(value) != 2:
        raise ValueError(f"reviewer {label} shape drifted")
    return [_number(item, label) for item in value]


def rebuild_actor_binding_literal(
    arm: Mapping[str, Any],
    *,
    execution_root_sha256: str,
    cluster_root_sha256: str,
    cluster_index: int,
    expected_arm: str,
) -> dict[str, Any]:
    if (
        execution_root_sha256 != EXPECTED_EXECUTION_ROOT
        or expected_arm not in EXPECTED_ARMS
        or arm.get("arm") != expected_arm
        or type(cluster_index) is not int
        or not 0 <= cluster_index < 100
        or type(cluster_root_sha256) is not str
        or len(cluster_root_sha256) != 64
    ):
        raise ValueError("reviewer actor authority binding drifted")
    ticks = arm.get("ticks")
    if type(ticks) is not list or len(ticks) != 64:
        raise ValueError("reviewer actor tick denominator drifted")
    receipts = []
    first_ids: tuple[str, ...] | None = None
    for tick_index, tick in enumerate(ticks):
        if type(tick) is not dict or tick.get("tick_index") != tick_index:
            raise ValueError("reviewer actor tick identity drifted")
        safety = tick.get("_safety_record")
        actors = safety.get("actors") if type(safety) is dict else None
        if type(actors) is not list:
            raise ValueError("reviewer actor stream missing")
        normalized = []
        ids = []
        for actor in actors:
            if type(actor) is not dict or set(actor) != set(
                EXPECTED_ACTOR_FIELDS
            ):
                raise ValueError("reviewer actor field set drifted")
            actor_id = str(actor["id"])
            ids.append(actor_id)
            row = {
                "id": actor_id,
                "position_xy": _vector(actor["position_xy"], "position"),
                "velocity_xy_mps": _vector(
                    actor["velocity_xy_mps"], "velocity"
                ),
                "heading_rad": _number(actor["heading_rad"], "heading"),
                "length_m": _number(actor["length_m"], "length"),
                "width_m": _number(actor["width_m"], "width"),
                "wheelbase_m": _number(actor["wheelbase_m"], "wheelbase"),
            }
            if min(row["length_m"], row["width_m"], row["wheelbase_m"]) <= 0:
                raise ValueError("reviewer actor dimensions are not positive")
            normalized.append(row)
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("reviewer actor IDs are not sorted unique")
        current_ids = tuple(ids)
        if first_ids is None:
            first_ids = current_ids
        elif current_ids != first_ids:
            raise ValueError("reviewer actor IDs drifted across ticks")
        receipts.append(
            {
                "execution_root_sha256": execution_root_sha256,
                "cluster_root_sha256": cluster_root_sha256,
                "cluster_index": cluster_index,
                "arm": expected_arm,
                "tick_index": tick_index,
                "actor_count": len(normalized),
                "actor_state_sha256": _canonical_sha(normalized),
            }
        )
    return {
        "schema_version": "camp_dp_v25_multiroute_sealed_actor_binding_v1",
        "execution_root_sha256": execution_root_sha256,
        "cluster_root_sha256": cluster_root_sha256,
        "cluster_index": cluster_index,
        "arm": expected_arm,
        "tick_count": 64,
        "actor_ids": list(first_ids or ()),
        "actor_count_per_tick": [row["actor_count"] for row in receipts],
        "tick_receipts": receipts,
        "binding_sha256": _canonical_sha(receipts),
        "legacy_supplementary_header_gate_used": False,
        "candidate0_special_case_used": False,
    }


__all__ = [
    "EXPECTED_ACTOR_FIELDS",
    "EXPECTED_AFFECTED_LEAF_SET_SHA",
    "EXPECTED_ARMS",
    "EXPECTED_AUTHORITY",
    "EXPECTED_EXECUTION_REVIEW_ROOT",
    "EXPECTED_EXECUTION_ROOT",
    "EXPECTED_PARENT_AUTHORITY",
    "EXPECTED_SUPERSEDED_EVALUATION_ROOT",
    "expected_affected_leaf_ids",
    "rebuild_actor_binding_literal",
    "review_contract_literal",
]
