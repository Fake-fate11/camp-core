from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs" / "diffusion_planner_v22_iteration_audit.md"
STATUS = ROOT / "docs" / "diffusion_planner_current_status.md"

POINTER = (
    "current_v22_status=v22_convex_selector_training_tdd_passed",
    "current_v22_artifact_source_head=fdbbf1c5e7a98d77847ce78895052fd0c710b565",
    "current_v22_prior_gate_final_synced_head=fdbbf1c5e7a98d77847ce78895052fd0c710b565",
    "current_v22_final_synced_head=pending_current_docs_commit_not_source_drift",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v22_artifact=/root/autodl-tmp/camp_dp_v22_convex_selector_training_tdd_fdbbf1c5_20260714T232226CST",
    "current_v22_artifact_root_sha256=e63260e1ed636672a42fa8f2f19ac2b3ba34093fb18af082c7f5f2f44a5d18fd",
    "next_work_target=v22_convex_selector_training_preflight_only",
)


def test_v22_audit_ends_with_authoritative_pointer() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    assert text.rstrip().endswith("\n".join(POINTER))


def test_current_status_v22_pointer_matches_audit() -> None:
    text = STATUS.read_text(encoding="utf-8")
    section = text.split("## Current V22 Status", 1)[1].split(
        "## Current V21 Status", 1
    )[0]
    for line in POINTER:
        assert section.count(line) == 1


def test_v22_freezes_route_retention_and_hard_invalid_boundary() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    for phrase in (
        "outcome-blind",
        "evaluation denominator",
        "must not be deleted, replaced, redrawn, or skipped",
        "all-K-high-risk/stress",
        "must not fail closed or force candidate 0",
        "NaN/Inf",
        "execution/source failure",
        "route coverage",
        "hard-invalid rate",
        "paired-complete rate",
        "before any CAMP or DP outcome is observed",
    ):
        assert phrase in text


def test_v22_preserves_fixed_candidate_and_no_claim_guards() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    for phrase in (
        "fixed K=8 candidate tensor",
        "score_k(w)=a_k^T w",
        "nonnegative simplex",
        "candidate 0",
        "formal seeds 11/12/13",
        "Full36",
        "honest no-claim",
        "V21 is historical and read-only",
    ):
        assert phrase in text


def test_v22_capability_audit_records_real_inventory_hard_stop() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    for phrase in (
        "7 existing route assets",
        "2 logical maps",
        "759 / 156",
        "totaling 915 deterministic",
        "map-identity zero-overlap is impossible",
        "No third existing",
        "user_decision_required_before_v22_map_zero_overlap_contract_change_or_new_map_assets",
        "No model was loaded",
    ):
        assert phrase in text


def test_v22_records_authorized_map_contract_resolution_without_rewriting_gate1() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "logical maps may be reused across splits",
        "route-family/corridor group",
        "route identity, route family, and seed namespace",
        "shared lanelet",
        "overlapping corridor",
        "before any CAMP or DP outcome",
        "map ID, route ID, and split identity are forbidden",
        "within the two fixed logical maps",
        "No unseen-map generalization claim",
        "future external-validation extension",
    ):
        assert phrase in text


def test_v22_records_frozen_route_family_split_and_independent_review() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "915 source routes",
        "759 / 152 / 4",
        "train/calibration/holdout route counts are 4 / 30 / 100",
        "32 / 90 / 500 expected paired runs",
        "00394a1ad67f6d760f8c12f28532c6f661663fe7709a233adb79dc3b05904bc8",
        "b231ba9fe425e40a129e30ce0b37044f1059354f84744d91911608f09f87baa5",
        "2ba80e30c40f92dac61bfe0996fd66f94e544c9a454429cb379bfe59afd7e7b6",
        "maximum reachable train count is exactly 4",
        "No CAMP or DP outcome was read",
        "holdout map is absent from train",
        "unseen-map generalization remains unauthorized",
        "claim_authorized=false",
    ):
        assert phrase in text


def test_v22_records_train_corpus_static_preflight_without_execution() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "train-only static preflight",
        "4 / 30 / 100 route counts",
        "8 / 3 / 5 seed counts",
        "32 train route-seed runs",
        "13 snapshots per complete 64-tick run",
        "theoretical ceiling is 416 snapshots",
        "no 5k/10k/20k/50k level is reachable",
        "v18_ablation_corpus_collection_only",
        "b1090808c9c3176eaf63cd92db8fbf6249d65e0549efdcc240492654f47f5370",
        "process-guard self-match",
        "No model was loaded and no simulator executed",
        "holdout outcomes were not read",
    ):
        assert phrase in text


def test_v22_records_decision_sink_and_content_addressed_writer() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "ticks 0, 5, and 10",
        "finite `8 x 14` atom matrix",
        "candidate tensor before/after SHA256 equality",
        "content-addressed snapshot",
        "identity fields only in the sidecar",
        "holdout snapshots are rejected",
        "failed route-seed receipt",
        "94db868dcbd2a7d2711dda8158ed90f6901c45442f2f173c2d0f343fbd3ff5de",
        "58 / 58",
        "No model was loaded and no simulator executed",
    ):
        assert phrase in text


def test_v22_records_corpus_execution_harness_preflight() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "32 / 32 frozen run configs",
        "CAMP collection arm only",
        "scenario, candidate, and spawn seed",
        "route-seed wall-clock",
        "stratum and all-K-high-risk snapshot counts",
        "stale next-work pointer",
        "3682434e21939e148f63a52640c7846e8130157926192b376ef32f91f160ea5f",
        "c635be46ae3d511c496af2d0175812ea3611acc71da8beed1d72651bae108387",
        "No model was loaded and no simulator executed",
        "v22_native_train_corpus_execution_only",
    ):
        assert phrase in text


def test_v22_records_first_corpus_as_execution_complete_but_evidence_no_pass() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "32 / 32 route-seed runs",
        "416 / 416 snapshots",
        "zero execution failures",
        "not a gate pass",
        "416 / 416 snapshots omit",
        "d270e094902401c791bebb21e6f88bf6e7a2bafae4f7daeaf874340156d5abb0",
        "c32c9110015b069f3300b5d3878ade0286d829f22aa0a42cff83504d14986983",
        "15c2444d73ef05742b88935e68d24fda946d9a40ee4974bf8417a17861996a6e",
        "default_output_sha256",
        "default_candidate0_identity",
        "69 / 69",
        "corrected train-corpus rerun",
        "No calibration or holdout outcome was read",
    ):
        assert phrase in text


def test_v22_records_corrected_corpus_and_full_independent_review() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "corrected train-only corpus execution",
        "1026.6618002699688 s",
        "32 / 32 route-seed runs",
        "416 / 416 snapshots",
        "a5ab6572eab37ecec6031e14a56755c71ef26b8ffd393d710ee32d40af8dfcb7",
        "9,514 independent checks",
        "416 / 416 DP operational default/candidate-0 identity receipts",
        "cf3622d49f8933e16868618b9dd7eaa6736b07a3978af22a1d4463df5402ecd1",
        "No 5k/10k/20k/50k learning-curve tier is reachable",
        "all 416 available snapshots",
        "No calibration or holdout route/outcome was executed or read",
        "v22_train_only_offline_label_contract_and_tdd_only",
    ):
        assert phrase in text


def test_v22_records_train_only_causal_label_materialization_and_review() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "v22_causal_soft_risk_surrogate_v1",
        "causal soft-risk surrogate, not an actual closed-loop outcome",
        "source-valid mask is the only eligibility boundary",
        "finite additive penalty of 100",
        "416 / 416 label sidecars",
        "12 / 404",
        "11 supported atoms",
        "lane_deviation, planned_red_light_cost, and red_stopping_margin_cost",
        "1da8ff585eca04c11fae9cd1a5629c4f077d26f050d075f97a6f5c1c9810a740",
        "86be3a18fb7f1fe3efdee1ee4a1c7b1399baac9c7421ea784d21b349bde89a4f",
        "3,759 independent checks",
        "f8e646e6b030efb2b613ec3a30b2a712e4a5fb55b79aa4daa386ee390560971c",
        "No calibration or holdout data or outcome was read",
        "No model was loaded and no simulator executed",
        "v22_convex_selector_training_tdd_only",
    ):
        assert phrase in text


def test_v22_records_convex_selector_training_tdd_without_execution() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "13 / 13",
        "CVXPY/CLARABEL",
        "all_available_416",
        "11 supported atoms",
        "strict zero learned weight",
        "clip(raw_atom/scale,0,10.0)",
        "v18 frozen corrected14d selector is ablation-only",
        "label-to-source root linkage",
        "solver invocation",
        "e63260e1ed636672a42fa8f2f19ac2b3ba34093fb18af082c7f5f2f44a5d18fd",
        "No production model was trained",
        "v22_convex_selector_training_preflight_only",
    ):
        assert phrase in text
