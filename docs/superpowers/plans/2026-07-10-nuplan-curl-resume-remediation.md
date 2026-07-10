# nuPlan Curl Resume Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the lossy in-process curl retry with bounded outer retries that preserve one existing mini `.part` file and never create extra download partials.

**Architecture:** Stop only the active curl child so the old wrapper records its exit and releases the acquisition lock. Preserve the existing mini partial in place, then launch one new evidence artifact whose command invokes a fresh curl process for every retry, pins the observed ETag with `If-Range`, rejects size regression, and keeps the existing size, SHA256, and ZIP checks.

**Tech Stack:** Bash, curl 7.81.0, flock, sha256sum, unzip, Paramiko, existing v18 audit/status documents.

## Global Constraints

- Keep CAMP on `main`; do not touch unrelated untracked files.
- Keep Diffusion Planner fixed at `7a1d33da277a1992ec474b5383a0c963c72e04e4` and tracked-clean.
- Preserve `/root/autodl-tmp/nuplan/downloads/nuplan-v1.1_mini.zip.part` in place.
- If that exact partial fails the size, ETag, or trailing-64-KiB Range hash check, delete only `/root/autodl-tmp/nuplan/downloads/nuplan-v1.1_mini.zip.part` and restart from byte `0`.
- The downloads directory may contain only `nuplan-maps-v1.0.zip` and `nuplan-v1.1_mini.zip.part` while the job runs.
- Do not use curl `--retry`, `--retry-all-errors`, or `--retry-delay`.
- Do not print or store AutoDL credentials or proxy values.

---

### Task 1: Prove the old command violates the retry contract

**Files:**
- Read: `/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_aws_acquisition_1fd91258_20260710T143617CST/COMMAND`
- Test: one-shot remote command-contract assertion

**Interfaces:**
- Consumes: the immutable old acquisition command.
- Produces: a RED result showing `--continue-at -` and internal `--retry` coexist.

- [x] **Step 1: Run the failing contract check**

```bash
command=/root/autodl-tmp/camp_dp_v18_nuplan_mini_official_aws_acquisition_1fd91258_20260710T143617CST/COMMAND
grep -q -- '--continue-at -' "$command" && ! grep -q -- '--retry' "$command"
```

Expected: exit `1`, because the old command contains internal retry flags.

### Task 2: Stop and finalize the old failed attempt

**Files:**
- Preserve: `/root/autodl-tmp/nuplan/downloads/nuplan-v1.1_mini.zip.part`
- Modify: old artifact evidence only (`run.exit`, failure classification, file inventory, SHA manifests)

**Interfaces:**
- Consumes: wrapper PID `439876` and its live curl child.
- Produces: a stopped wrapper, released lock, preserved partial, and immutable failure evidence.

- [x] **Step 1: Record the live process and download inventory**
- [x] **Step 2: Send TERM only to the curl child and wait for wrapper PID `439876` to exit**
- [x] **Step 3: Verify the mini partial still exists and no extra `.part` file exists**
- [x] **Step 4: Compare the partial's trailing 64 KiB with the same ETag-pinned remote Range without writing a probe file**
- [x] **Step 5: If the check fails, delete only the literal mini `.part`; otherwise preserve it in place**
- [x] **Step 6: Write the failure class and SHA manifests inside the old artifact**

### Task 3: Launch the fixed one-part acquisition

**Files:**
- Create: one new AutoDL evidence artifact containing `COMMAND`, `HEADS`, `SOURCE_METADATA`, `PID`, `stdout.txt`, and `stderr.txt`.
- Reuse: `/root/autodl-tmp/nuplan/downloads/nuplan-v1.1_mini.zip.part`.
- Delete and recreate that same path only if the resume qualification check fails.

**Interfaces:**
- Consumes: the preserved partial, expected size `8550100030`, and ETag `"08abc074db9227e758cc41c6b1ee223c-1020"`.
- Produces: one locked acquisition process with bounded outer retries.

- [x] **Step 1: Write a command whose retry core is exactly one fresh curl per loop iteration**

```bash
failures=0
while :; do
  before=$(stat -c %s "$part" 2>/dev/null || printf 0)
  printf 'attempt name=%s number=%s offset=%s\n' "$name" "$((failures + 1))" "$before"
  if curl --fail --location --silent --show-error --continue-at - \
      --header "If-Range: $expected_etag" \
      --connect-timeout 30 --speed-time 120 --speed-limit 1024 \
      --output "$part" "$url"; then
    break
  else
    code=$?
  fi
  after=$(stat -c %s "$part" 2>/dev/null || printf 0)
  if [ "$after" -lt "$before" ]; then
    printf 'partial_size_regressed name=%s before=%s after=%s\n' "$name" "$before" "$after" >&2
    return 5
  fi
  failures=$((failures + 1))
  printf 'outer_retry name=%s failure=%s curl_exit=%s bytes=%s\n' "$name" "$failures" "$code" "$after" >&2
  if [ "$failures" -ge 20 ]; then
    return "$code"
  fi
  sleep 5
done
```

- [x] **Step 2: Verify RED becomes GREEN**

Run the Task 1 contract against the new `COMMAND`.

Expected: exit `0`; `bash -n COMMAND` also exits `0`.

- [x] **Step 3: Start exactly one wrapper under the acquisition lock**
- [x] **Step 4: Verify its first log line resumes at the preserved byte count**
- [x] **Step 5: Sample size growth and assert the downloads directory still contains exactly two files and one `.part`**

### Task 4: Audit and checkpoint

**Files:**
- Modify: `docs/diffusion_planner_v18_iteration_audit.md`
- Modify: `docs/diffusion_planner_current_status.md`
- Include: `docs/superpowers/plans/2026-07-10-nuplan-curl-resume-remediation.md`

**Interfaces:**
- Consumes: old failure artifact and new running artifact evidence.
- Produces: verified running-state EOF, local/GitHub/AutoDL alignment, and one checkpoint commit.

- [x] **Step 1: Append the root cause, old failure evidence, new PID/artifact, ETag, preserved offset, and no-pollution inventory**
- [x] **Step 2: Run `py_compile`, focused causal tests, v18 document checks, and `git diff --check`**
- [ ] **Step 3: Commit only the plan and two status documents, push `main`, and fast-forward AutoDL CAMP**
- [ ] **Step 4: Re-read the v18 EOF and stop while the corrected acquisition runs**
