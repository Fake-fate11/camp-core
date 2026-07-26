from __future__ import annotations

from copy import deepcopy

import pytest

from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2_replacement import (
    AUTHORITY_SHA256,
    build_scene_adapter,
    build_signal_authority,
    reconstruct_controlled_case,
    replacement_contract,
    replacement_exact_dirs,
    semantic_runtime_receipt,
    validate_replacement_contract,
)
from camp_core.integrations.diffusion_planner_v25_industrial_multiroute_v2_replacement_review import (
    literal_semantic_receipt,
    review_contract_semantics,
)
from camp_core.integrations.diffusion_planner_v25_project_authored_multiroute_source import (
    build_source_record,
)


IMPLEMENTATION = "12" * 20
CONTINUATION = "34" * 32


def _contract() -> dict:
    return replacement_contract(
        implementation_head=IMPLEMENTATION,
        replacement_continuation_sha256=CONTINUATION,
        replacement_continuation_root="56" * 32,
        replacement_continuation_review_root="78" * 32,
        old_attempt_closeout_root="9a" * 32,
        old_attempt_closeout_review_root="bc" * 32,
    )


def test_contract_exact_denominator_dirs_and_independent_review() -> None:
    value = validate_replacement_contract(_contract())
    assert AUTHORITY_SHA256 == (
        "c065e1b08e711a6cdeb84c14f94d5941019f613562ac452c028e8f903b537866"
    )
    assert value["exact_dirs"] == replacement_exact_dirs(
        IMPLEMENTATION, CONTINUATION
    )
    assert value["replacement_denominator"]["planned_tick_slots"] == 19_200
    assert value["formal_runtime_semantics"]["dryrun_receipt_count"] == 16_128
    review_contract_semantics(value)


def test_red_family_no_signal_is_formally_none_after_source_equality() -> None:
    record = build_source_record(159)["record"]
    assert record["cell"]["family"] == "red_light_phase_timing"
    assert record["cell"]["source_availability"] == "no_signal"
    assert record["semantic_block"]["signal_semantics"]["phase"] in {
        "yellow",
        "red",
    }
    case = reconstruct_controlled_case(record)
    assert case["signal"] == {
        "phase": "none",
        "mapped_source_required": False,
    }
    assert case["phase_authority_mode"] is None
    mapped, absent = build_signal_authority(record, case)
    assert mapped is None
    assert absent is not None
    assert absent["traffic_light_regulatory_element_ids"] == []
    assert absent["semantic_clone_payload"]["signal"] == {
        "current_phase": "none",
        "mapped_source_required": False,
        "source_mode": "no_v2i",
    }
    assert build_scene_adapter(record).no_signal_authority is not None


def test_all_252_sources_match_independent_literal_oracle() -> None:
    phase_counts = {"green": 0, "yellow": 0, "red": 0}
    source_counts = {"mapped_signal": 0, "no_signal": 0}
    for ordinal in range(252):
        record = build_source_record(ordinal)["record"]
        producer = semantic_runtime_receipt(record, ordinal % 64)
        reviewer = literal_semantic_receipt(record, ordinal % 64)
        assert producer == reviewer
        source_counts[producer["source_availability"]] += 1
        if producer["source_availability"] == "no_signal":
            assert producer["formal_phase"] == "none"
            assert producer["formal_mapped_source_required"] is False
            assert producer["formal_signal_object_counts"] == {
                "regulatory": 0,
                "physical_light": 0,
                "bulb": 0,
                "stopline": 0,
            }
        else:
            phase_counts[producer["formal_phase"]] += 1
            assert producer["formal_mapped_source_required"] is True
            assert producer["same_tick_phase_authority"] is True
        assert producer["future_phase_consumed"] is False
        assert producer["future_schedule_consumed"] is False
    assert source_counts == {"mapped_signal": 126, "no_signal": 126}
    assert all(phase_counts[phase] > 0 for phase in phase_counts)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("formal_phase",), "yellow"),
        (("formal_mapped_source_required",), True),
        (("future_schedule_consumed",), True),
        (("formal_signal_object_counts", "stopline"), 1),
    ],
)
def test_no_signal_receipt_mutation_is_rejected(path: tuple[str, ...], value) -> None:
    record = build_source_record(159)["record"]
    receipt = semantic_runtime_receipt(record, 0)
    mutated = deepcopy(receipt)
    target = mutated
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert mutated != literal_semantic_receipt(record, 0)


def test_source_repin_and_contract_mutations_fail_closed() -> None:
    record = build_source_record(159)["record"]
    record["cell"]["source_availability"] = "mapped_signal"
    with pytest.raises(ValueError):
        reconstruct_controlled_case(record)
    value = _contract()
    value["replacement_denominator"]["old_partial_reuse"] = True
    with pytest.raises(ValueError):
        validate_replacement_contract(value)
    value = _contract()
    value["formal_runtime_semantics"]["no_signal"]["phase"] = "red"
    value["contract_sha256"] = __import__("hashlib").sha256(
        (
            __import__("json").dumps(
                {key: item for key, item in value.items() if key != "contract_sha256"},
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("ascii")
    ).hexdigest()
    with pytest.raises(ValueError):
        review_contract_semantics(value)
