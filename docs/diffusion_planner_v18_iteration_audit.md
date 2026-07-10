# DP-CAMP V18 nuPlan Iteration Audit

Last verified: 2026-07-10, Asia/Shanghai.

This is the append-only gate ledger for the v18 nuPlan mini to causal nuPlan
10k path. Historical v14-v17 conclusions remain in their original audits.

## Fixed Boundary

- Diffusion Planner remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`; its code, configuration,
  weights, and checkpoint are immutable.
- K is fixed at 8. CAMP may only score, rerank, and select the fixed candidate
  tensor; it may not generate, repair, rewrite, blend, or postprocess a
  trajectory.
- The score remains `score_k(w)=a_k^T w`; weights are a nonnegative simplex
  over approved atoms, and CVaR/L2/master remain convex.
- Decision-time inputs, canonical `dp_camp_v10_14d` atoms, split seeds, data
  isolation, fail-closed rules, evidence requirements, claim criteria, and
  stop conditions are those in the active Codex goal objective.
- Old nuScenes corpora and artifacts are historical only and may not be
  restored, revalidated, or reused for v18.

## Gate 0: V17 Supersession and V18 Bootstrap

Status: local preflight ready; checkpoint, push, and AutoDL fast-forward
verification remain pending.

- V17 EOF was read and closed only with
  `v17_nuscenes_path_superseded_by_user_decision_and_artifacts_deleted`; its
  missing-input blocker was not resumed.
- Local branch: `main`.
- Pre-transition local CAMP HEAD / GitHub `main` / AutoDL CAMP HEAD / AutoDL
  `origin/main`:
  `db3376866181fdcd97c926c6c1d6e28e516c2fcd`.
- Local and AutoDL CAMP tracked status: clean. Unrelated local untracked files
  were not modified.
- AutoDL Diffusion Planner HEAD / tracked status:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4 / clean`.
- AutoDL `/root/autodl-tmp` contains only `.autodl`, `camp_core`,
  `Diffusion-Planner`, `camp_dp_assets`, and `dp312_venv`, with approximately
  `42G` available. No v17/v18 generation, training, or evaluation job is
  active.
- nuPlan source inventory and acquisition were not executed by this docs-only
  bootstrap. No substitute or synthetic dataset was created.
- Candidate tensors, corpus rows, splits, weights, metrics, training time, and
  selector latency: not applicable at this gate.
- Local v18 document-contract self-check and `git diff --check`: passed.
- Python 3.12 `py_compile` for the causal materializer and atom gate: passed.
- Focused causal materializer/availability tests: `19 passed, 1 skipped`; the
  skip is the environment-gated fixed-DP contract test.

current_v18_status=v18_nuplan_mini_source_inventory_pending
current_v18_artifact_scope=v17_supersession_and_v18_nuplan_bootstrap
current_v18_artifact=docs/diffusion_planner_v18_iteration_audit.md
next_work_target=v18_nuplan_mini_source_inventory_and_acquisition_preflight_only

### Gate 0 Checkpoint and Cross-Surface Verification

Status: passed.

- Bootstrap checkpoint:
  `b43bae6eb559c6185e2702386c0aa7dd8167489b`.
- Local CAMP HEAD, GitHub `main`, AutoDL CAMP HEAD, and AutoDL `origin/main`
  equaled the checkpoint when verified; local and AutoDL tracked states were
  clean.
- AutoDL Diffusion Planner remained tracked-clean at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- AutoDL document SHA256:
  - current status:
    `1da4f219f4fb9bda5abd90a7878fac9bb3804ea42b4e3c2c5eb399e9fe374975`
  - v17 audit with supersession marker:
    `38a07e09c78182b6284a1a0641a4cae53f3286181b34d8f83e6704c85fc43977`
  - v18 audit bootstrap:
    `95992bcbdc916d63180e3dac71c0767ae8cf705d7629f2ecbea256de2eb97628`
- No v17/v18 generation, training, or evaluation job was active. No nuPlan
  source inventory, acquisition, candidate generation, training, evaluation,
  claim, promotion, deployment, or activation occurred in this gate.

current_v18_status=v18_nuplan_mini_source_inventory_pending
current_v18_artifact_scope=v17_supersession_and_v18_nuplan_bootstrap_verified
current_v18_artifact=docs/diffusion_planner_v18_iteration_audit.md
next_work_target=v18_nuplan_mini_source_inventory_and_acquisition_preflight_only

## Gate 1: nuPlan Mini Source Inventory and Acquisition Preflight

Status: source inventory passed; acquisition stopped before download at the
manual license-authorization boundary.

- Evidence artifact:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_source_inventory_preflight_eff4f89a_20260710T142636CST`
- Artifact root SHA256:
  `1cdae5c6a7543f8575abca44d25b9a552dca88eb1add9757654add33a0df41c0`
- JSON / MD SHA256:
  `8f47fe1f735f6bd2f3f18a2d1e49467dbe627ee60cdaf56b9fdca9639741666d` /
  `c736fffcfd91193355df6051ab250ef6fa08c0d2e19a58ced208acdd826d7531`.
- `SHA256SUMS` and `ROOT_SHA256SUMS` verification: passed; all preflight
  checks passed and `run.exit=0`.
- CAMP HEAD / origin:
  `eff4f89a872e3e4cf897ecefc1c59a5fcc131afe`; tracked clean.
- Fixed DP HEAD / tracked status:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4 / clean`.
- Fixed DP native nuPlan references, loader, and config: `0 / none / none`.
  Its native dataset surface is a JSON list, or a `files` dict, of NPZ paths
  loaded by `DiffusionPlannerData`.
- Bounded source search under `/root/autodl-tmp` and `/autodl-pub/data`, to
  depth 5, found zero nuPlan-named source paths. Available data-disk space was
  `45045547008` bytes. No v17/v18 job was active.
- Official source inventory:
  - registry: `https://registry.opendata.aws/motional-nuplan/`
  - maps archive: `971557640` bytes, HTTP `200`
  - mini archive: `8550100030` bytes, HTTP `200`
  - compressed total: `9521657670` bytes
- The official website/setup path requires an account and agreement to the
  Motional Dataset Terms. The official AWS Open Data copy requires no AWS
  account, but anonymous access does not remove those terms. The terms apply to
  downloads from the website or elsewhere, allow eligible non-commercial use,
  and require a commercial license for commercial use.
- Non-commercial eligibility, user acceptance, and commercial-license
  authorization are all unconfirmed. No agent may accept that legal boundary
  on the user's behalf, so no archive was downloaded or extracted.
- Data records / split / K: `0 / none / 8` (contract only). Weights, metrics,
  training time, selector latency, and reranking overhead: not applicable.
- No adapter implementation, candidate generation, atom materialization,
  training, holdout access, evaluation, claim, promotion, deployment, or
  activation occurred.

current_v18_status=v18_nuplan_mini_source_inventory_passed_acquisition_blocked_pending_license_authorization
current_v18_artifact_scope=nuplan_mini_source_inventory_and_acquisition_preflight
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_source_inventory_preflight_eff4f89a_20260710T142636CST
current_v18_artifact_root_sha256=1cdae5c6a7543f8575abca44d25b9a552dca88eb1add9757654add33a0df41c0
next_work_target=user_confirmation_of_noncommercial_terms_acceptance_or_commercial_nuplan_license_before_acquisition
