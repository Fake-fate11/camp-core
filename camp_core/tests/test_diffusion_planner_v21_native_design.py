from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DESIGN = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-07-14-v21-native-simulator-paired-closed-loop-design.md"
)


def test_design_selects_thin_native_hook_without_dp_changes() -> None:
    text = " ".join(DESIGN.read_text(encoding="utf-8").split()).lower()
    required = (
        "CAMP-side thin hook",
        "run_route_replay",
        "DP modification is a hard stop",
        "sg_smooth_enabled=false",
        "max_steps=64",
        "candidate 0 reuses the direct operational output bytes",
        "native MPC",
    )
    for phrase in required:
        assert phrase.lower() in text


def test_design_freezes_causal_paired_and_selector_contracts() -> None:
    text = " ".join(DESIGN.read_text(encoding="utf-8").split()).lower()
    required = (
        "native_zero_left_pad_to_31_v1",
        "observed_frames",
        "padded_frames",
        "input_sha256",
        "score_k(w)=a_k^T w",
        "nonnegative simplex",
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "closed-loop outcomes are forbidden",
    )
    for phrase in required:
        assert phrase.lower() in text


def test_design_preregisters_safety_cost_and_no_claim_boundary() -> None:
    text = " ".join(DESIGN.read_text(encoding="utf-8").split()).lower()
    required = (
        "SafetyCost Native v1",
        "100 * collision_any",
        "10 * near_miss_noncollision_rate",
        "20 * offroad_rate",
        "20 * wrong_way_rate",
        "30 * red_light_violation_any",
        "10 * speed_limit_violation_rate",
        "sample_map_tl_route_59_to_86.pkl",
        "formal seeds 11/12/13",
        "smoke cannot support a safety or CAMP>DP claim",
        "CI95 upper bound",
        "five-point drivable coverage",
        "no Shapely dependency",
    )
    for phrase in required:
        assert phrase.lower() in text
