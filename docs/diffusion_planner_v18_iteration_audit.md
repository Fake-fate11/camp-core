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
