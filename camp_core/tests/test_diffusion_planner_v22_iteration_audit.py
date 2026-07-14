from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs" / "diffusion_planner_v22_iteration_audit.md"
STATUS = ROOT / "docs" / "diffusion_planner_current_status.md"

POINTER = (
    "current_v22_status=v22_route_family_split_frozen_with_4_route_training_ceiling",
    "current_v22_artifact_source_head=b36f98ae0c0efb2b55fcbe442172a0e6b52389fe",
    "current_v22_prior_gate_final_synced_head=b36f98ae0c0efb2b55fcbe442172a0e6b52389fe",
    "current_v22_final_synced_head=pending_current_docs_commit_not_source_drift",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v22_artifact=/root/autodl-tmp/camp_dp_v22_route_family_split_freeze_independent_review_b36f98ae_20260714T210148CST",
    "current_v22_artifact_root_sha256=2ba80e30c40f92dac61bfe0996fd66f94e544c9a454429cb379bfe59afd7e7b6",
    "next_work_target=v22_native_train_corpus_static_preflight_with_frozen_4_route_training_ceiling_only",
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
