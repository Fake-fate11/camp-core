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

## Gate 2: Non-Commercial Dataset Authorization

Status: authorization recorded; acquisition execution is the only next gate.

The user confirmed all of the following:

- the project is limited to personal, academic, or other non-commercial
  research;
- the project has no present or future revenue purpose;
- the Motional Dataset Terms were read and accepted;
- the official Motional AWS anonymous source is authorized for nuPlan mini
  acquisition and use; and
- raw nuPlan data must not be redistributed.

This resolves the Gate 1 manual-license blocker without changing the fixed DP,
K=8, causal-input, atom, split, convexity, or claim boundaries. It authorizes
only the official maps and mini archive acquisition. No archive was downloaded
or extracted by this docs-only authorization gate, and no adapter, candidate,
atom, training, evaluation, claim, promotion, deployment, or activation work
occurred.

current_v18_status=v18_nuplan_mini_noncommercial_license_authorization_recorded
current_v18_artifact_scope=nuplan_mini_noncommercial_terms_acceptance_and_no_raw_redistribution_authorization
current_v18_artifact=docs/diffusion_planner_v18_iteration_audit.md
next_work_target=v18_nuplan_mini_official_aws_maps_and_mini_acquisition_execution_only

## Gate 3: Official AWS Acquisition Execution

Status: running; stop and monitor only. Do not launch a second acquisition.

- Authorization checkpoint CAMP HEAD / origin / AutoDL:
  `1fd912587dd416bac091eb76c976a38c64051903`.
- Fixed DP HEAD / tracked status:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4 / clean`.
- Execution artifact:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_aws_acquisition_1fd91258_20260710T143617CST`
- AutoDL PID: `439876`.
- Started: `2026-07-10T14:36:22+08:00`.
- The single resumable command downloads the official maps archive first and
  the mini archive second, using `.part` files and an exclusive acquisition
  lock. It requires the audited sizes `971557640` and `8550100030` bytes,
  generates `ARCHIVE_SHA256SUMS`, and runs ZIP integrity checks before exit.
- First observation at approximately 30 seconds:
  - process: running
  - maps partial: `1867776` bytes
  - `run.exit`: pending
  - stderr tail: empty
  - data-disk available: approximately `42G`
- A later live process check confirmed the active `curl` inherited the
  `http_proxy` and `https_proxy` environment keys from `/etc/network_turbo`;
  proxy values were not printed or stored. The maps partial had grown to
  `11862016` bytes and the process remained active.
- Artifact/root SHA: pending until the job exits and the evidence package is
  finalized.
- No mini bytes, extraction, adapter implementation, candidate generation,
  atom materialization, split, training, evaluation, claim, promotion,
  deployment, activation, or raw-data redistribution occurred at this
  observation.

current_v18_status=v18_nuplan_mini_official_aws_acquisition_running
current_v18_artifact_scope=nuplan_mini_official_aws_maps_and_mini_archive_acquisition
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_aws_acquisition_1fd91258_20260710T143617CST
next_work_target=stop_while_v18_nuplan_mini_official_aws_acquisition_job_running_monitor_only

### Gate 3 Retry Remediation: Fresh Curl Per Attempt

Status: corrected acquisition running; stop and monitor only.

- Root cause: AutoDL curl `7.81.0` combined `--continue-at -` with
  `--retry 20 --retry-all-errors`. The mini invocation started without a
  partial, so its initial resume offset was zero. After two curl exit-18
  transfers, in-process retry restored the output toward that initial offset
  instead of preserving the latest partial length.
- Source capability was not the blocker. An ETag-pinned byte-range probe
  returned HTTP `206`, `Content-Range: bytes
  123456789-123456799/8550100030`, and mini ETag
  `"08abc074db9227e758cc41c6b1ee223c-1020"`.
- RED command-contract check against the old `COMMAND`: exit `1`, as expected,
  because `--continue-at -` and internal `--retry` coexisted.
- Old artifact:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_aws_acquisition_1fd91258_20260710T143617CST`
- Old wrapper / terminated curl / recorded exit:
  `439876 / 440416 / 143`.
- Old failure class / finalized root SHA256:
  `curl_internal_retry_resets_resume_offset` /
  `9e4705e5e6ac00eb378d10e28ed8b5cf65033e6e0e284f88f14276a638bedb02`.
- The partial was `370872320` bytes before and after stopping. Its trailing
  64 KiB local SHA256 and corresponding remote Range SHA256 both equaled
  `bdbe865516fc5458294670b9f719317c9f4009b9b54abf8b8a7d51ab0c150f73`.
  The ETag and Range probe passed, so the partial was preserved. The approved
  fallback deletes only the literal mini `.part` if size, ETag, Range, curl
  exit 33/36, or monotonicity proves it cannot resume; no backup is created.
- Corrected artifact:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_aws_acquisition_outer_retry_2d92202d_20260710T165604CST`
- Corrected wrapper PID / start:
  `443827 / 2026-07-10T16:56:07+08:00`.
- The corrected command passed `bash -n` and the GREEN contract check. It has
  no curl `--retry*` flag, uses at most 20 outer attempts, starts a fresh curl
  per attempt, pins `If-Range`, and retains the exact-size, SHA256, and ZIP
  integrity checks.
- Resume log: `bytes=370872320`; first active curl PID: `443843`.
- Same-inode 20-second sample:
  `374747136 -> 378183680` bytes (`+3436544`).
- Download inventory while running:
  `nuplan-maps-v1.0.zip=971557640` and exactly one
  `nuplan-v1.1_mini.zip.part`; total files / partial files: `2 / 1`.
- Maps / mini ETags:
  `"4581f21a3562c097041ab68f2d1177d9-116"` /
  `"08abc074db9227e758cc41c6b1ee223c-1020"`.
- Corrected launch JSON / MD / immutable launch-root SHA256:
  `665f17a60b3796ffb15c7c628b808ab9662bb8c28cdf6eec756b55fb8c6fdd39` /
  `b673b5c106cdb87d5d4d356b5771eea092e062eb6cb258ce57e8284d2adc5dbb` /
  `339af1f78a2bf91ec1d25817b6dea165fe3c923bfaa3bef43fb31aa0c46a8d3f`.
- Pre-launch CAMP HEAD / origin / tracked changes:
  `2d92202d1f0161762e6c6d3adb08c2d9a1207947` /
  `2d92202d1f0161762e6c6d3adb08c2d9a1207947` / `0`.
- Fixed DP HEAD / tracked changes:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4 / 0`.
- No extraction, adapter work, candidate generation, atom materialization,
  split, training, evaluation, claim, promotion, deployment, activation, raw
  data redistribution, duplicate acquisition, or additional partial occurred.

current_v18_status=v18_nuplan_mini_official_aws_acquisition_running
current_v18_artifact_scope=nuplan_mini_official_aws_acquisition_outer_retry_resume_remediation
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_aws_acquisition_outer_retry_2d92202d_20260710T165604CST
current_v18_old_failed_artifact_root_sha256=9e4705e5e6ac00eb378d10e28ed8b5cf65033e6e0e284f88f14276a638bedb02
current_v18_launch_root_sha256=339af1f78a2bf91ec1d25817b6dea165fe3c923bfaa3bef43fb31aa0c46a8d3f
next_work_target=stop_while_v18_nuplan_mini_official_aws_acquisition_job_running_monitor_only

### Gate 3 Retry Remediation Checkpoint Verification

Status: passed; corrected acquisition still running, so stop and monitor only.

- Remediation checkpoint local / GitHub / AutoDL CAMP HEAD and AutoDL origin:
  `1528681fc612920babfe39b8a1bbddaae63a9f24`.
- Local and AutoDL CAMP tracked states: clean. Unrelated local untracked files
  were not staged or modified.
- AutoDL fixed DP HEAD / tracked state:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4 / clean`.
- Local and AutoDL causal `py_compile`: passed.
- Local focused tests: `19 passed, 1 skipped in 1.40s`.
- AutoDL focused tests: `19 passed, 1 skipped in 0.81s`.
- Old failure artifact `SHA256SUMS` / root verification and corrected launch
  artifact `LAUNCH_SHA256SUMS` / launch-root verification: all passed.
- During AutoDL checkpoint verification, the same active job grew from
  `586768384` to `588849152` bytes (`+2080768`) without size regression.
- The active child command contains no `--retry*`; stderr remained empty.
- Download directory remained exactly two files with one partial:
  `nuplan-maps-v1.0.zip` and `nuplan-v1.1_mini.zip.part`.
- No duplicate task, backup partial, extra part file, extraction, adapter work,
  candidate generation, atom materialization, split, training, evaluation,
  claim, promotion, deployment, activation, or raw-data redistribution
  occurred.

current_v18_status=v18_nuplan_mini_official_aws_acquisition_running
current_v18_artifact_scope=nuplan_mini_official_aws_acquisition_outer_retry_resume_remediation_verified
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_aws_acquisition_outer_retry_2d92202d_20260710T165604CST
current_v18_old_failed_artifact_root_sha256=9e4705e5e6ac00eb378d10e28ed8b5cf65033e6e0e284f88f14276a638bedb02
current_v18_launch_root_sha256=339af1f78a2bf91ec1d25817b6dea165fe3c923bfaa3bef43fb31aa0c46a8d3f
next_work_target=stop_while_v18_nuplan_mini_official_aws_acquisition_job_running_monitor_only

### Gate 3 Acquisition Result Review

Status: passed; official archive extraction is the only next gate.

- Corrected acquisition completed at `2026-07-10T20:01:34+08:00` with
  `run.exit=0`.
- The first fresh curl attempt began at byte `370872320`, exited `18` after
  preserving `5964344032` bytes, and the outer loop's second fresh curl began
  at that exact offset. This is direct runtime evidence that the remediation
  accumulated progress across connection failure.
- Final maps / mini sizes:
  `971557640 / 8550100030` bytes.
- Final maps / mini SHA256:
  `d0310009fa9e8dd88014038336538aca678842c009fbf03fae76ed28f702ffc6` /
  `a3fe40afd81cc634884f8d0b7ea3604f2e617e365d5c258c61cfdd833c8d987b`.
- Independent `sha256sum -c` and `unzip -tq` review: passed for both archives.
- Download directory final files / partial files: `2 / 0`; no duplicate,
  backup, or orphan partial exists.
- Result JSON / MD SHA256:
  `68824c4cbbbee54420b279cb54a2ad6f0e81f9b5d5ffe7126b2e8c4441030448` /
  `4104065f4b70b9780ea3c6943d1e5e2044f7d7cc3a7cb1449c8b27d98329f473`.
- Final artifact root SHA256:
  `4d0a77dfab9f649df65e138fa41139afea01e2fc51144a4da897722a0a7c76c9`.
- CAMP HEAD / origin / tracked changes at result review:
  `88460d701eeda4788d2352c17c63d7292b5d6877` /
  `88460d701eeda4788d2352c17c63d7292b5d6877` / `0`.
- Fixed DP HEAD / tracked changes:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4 / 0`.
- No extraction, adapter implementation, candidate generation, atom
  materialization, split, training, evaluation, claim, promotion, deployment,
  activation, or raw-data redistribution occurred in this result review.

current_v18_status=v18_nuplan_mini_official_aws_acquisition_complete_verified
current_v18_artifact_scope=nuplan_mini_official_aws_acquisition_result_review
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_aws_acquisition_outer_retry_2d92202d_20260710T165604CST
current_v18_artifact_root_sha256=4d0a77dfab9f649df65e138fa41139afea01e2fc51144a4da897722a0a7c76c9
next_work_target=v18_nuplan_mini_official_archives_extraction_execution_only

## Gate 4: Official Archive Extraction Execution

Status: running; stop and monitor only. Do not launch a second extraction.

- Extraction artifact:
  `/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_archives_extraction_29eee9c9_20260710T204004CST`
- AutoDL PID / start:
  `450283 / 2026-07-10T20:40:05+08:00`.
- Target dataset root: `/root/autodl-tmp/nuplan/dataset`; it did not exist at
  preflight, and the command holds an exclusive extraction lock.
- ZIP path-safety review: passed; no absolute path, `..`, or symlink entry.
- Both archive `LICENSE` entries are identical: size `25319`, SHA256
  `1a218286e733f6d6135fc5698d614cda2be94ea096f6eee280278458e570636a`.
  The second identical license is skipped instead of overwritten.
- Expected unique extracted bytes / available bytes before launch:
  `15777787771 / 35522355200`.
- Expected final files / map files / mini SQLite databases:
  `72 / 7 / 64`.
- The command re-verifies source archive SHA256 before extraction, validates
  all 64 SQLite headers and readable schemas after extraction, and creates a
  full extracted-file SHA256 manifest.
- First observation: PID alive, `run.exit` pending, and approximately
  `1182928415` bytes existed under the dataset root.
- Launch JSON / MD / immutable launch-root SHA256:
  `86f33e27ebaad5b8bfb15165dfbb304bb73486768a5a55298f23fd25c55c42eb` /
  `4511e4d400cfcfa49c8c9ca838fb7c64cb757f4f79696cb1b2d9c3ccd2b8f2f8` /
  `ab340899aab8f5714559328499e7e11926160291d2815501f4ace2bf05d0e42f`.
- Launch CAMP HEAD / origin / fixed DP HEAD:
  `29eee9c99f55bfb773b7166b03e456035ca621af` /
  `29eee9c99f55bfb773b7166b03e456035ca621af` /
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- No adapter implementation, candidate generation, atom materialization,
  split, training, evaluation, claim, promotion, deployment, activation, raw
  data redistribution, duplicate extraction, or extra partial occurred.

current_v18_status=v18_nuplan_mini_official_archives_extraction_running
current_v18_artifact_scope=nuplan_mini_official_archives_official_hierarchy_extraction
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_archives_extraction_29eee9c9_20260710T204004CST
current_v18_launch_root_sha256=ab340899aab8f5714559328499e7e11926160291d2815501f4ace2bf05d0e42f
next_work_target=stop_while_v18_nuplan_mini_official_archives_extraction_job_running_monitor_only

### Gate 4 Extraction Result Review

Status: passed; causal-adapter source-contract inventory/test preflight is the
only next gate.

- Extraction completed at `2026-07-10T20:43:14+08:00` with `run.exit=0` and
  empty stderr.
- Dataset root: `/root/autodl-tmp/nuplan/dataset`.
- Extracted files / unique bytes / map files / mini SQLite databases:
  `72 / 15777787771 / 7 / 64`.
- All 64 SQLite headers and schemas were readable; every database exposed
  exactly 12 tables.
- Extracted-file SHA256 verification: `72 / 72` passed.
- Dataset manifest root SHA256:
  `43d09389dafd53f8486e9305fca005dede2ae8ba5aa97d908953a7084c435c72`.
- Result JSON / MD SHA256:
  `1d24d652a774fc3df24984a90f5c5fd89b507de1985433805a7f30ca5279d4e2` /
  `8552c6d7fea739a7d7a128a0a4cb79e5ac3c3fdd2050fcdb6a108e0b63ccb768`.
- Final extraction artifact root SHA256:
  `25edf589f115bcda2a24937d5b64d8ea317b5ee61d75a0429b506e58a1806dbd`.
- Available data-disk bytes after extraction: `19744247808`.
- CAMP HEAD / origin / tracked changes at result review:
  `d8f29b37fc16c472c203c80d4b0680d429b5569b` /
  `d8f29b37fc16c472c203c80d4b0680d429b5569b` / `0`.
- Fixed DP HEAD / tracked changes:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4 / 0`.
- No adapter implementation, candidate generation, atom materialization,
  split, training, evaluation, claim, promotion, deployment, activation, or
  raw-data redistribution occurred in this result review.

current_v18_status=v18_nuplan_mini_official_archives_extraction_complete_verified
current_v18_artifact_scope=nuplan_mini_official_archives_extraction_result_review
current_v18_artifact=/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_archives_extraction_29eee9c9_20260710T204004CST
current_v18_artifact_root_sha256=25edf589f115bcda2a24937d5b64d8ea317b5ee61d75a0429b506e58a1806dbd
next_work_target=v18_nuplan_mini_causal_adapter_source_contract_inventory_and_test_preflight_only
