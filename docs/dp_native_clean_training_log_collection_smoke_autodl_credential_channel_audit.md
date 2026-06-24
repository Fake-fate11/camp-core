# DP Native Clean Training Log Collection Smoke AutoDL Credential Channel Audit

Date: 2026-06-24

Gate:

```text
dp_native_clean_training_log_collection_smoke_autodl_noninteractive_execution_required
```

## Ref Evidence

```text
git status --short --branch
## main...origin/main
untracked unrelated session/slide artifacts remain ignored

git fetch --prune origin
exit=0

git rev-parse HEAD origin/main
3dec12c18935a21e4c70fa69fa33ae772d1724ab
3dec12c18935a21e4c70fa69fa33ae772d1724ab

git ls-remote origin refs/heads/main
3dec12c18935a21e4c70fa69fa33ae772d1724ab refs/heads/main
```

Current audit tail names this gate as the only admissible gate:

```text
dp_native_clean_training_log_collection_smoke_autodl_noninteractive_execution_required
```

## Local Credential Channel Checks

Available OpenSSH tools:

```text
ssh.exe       C:\WINDOWS\System32\OpenSSH\ssh.exe
scp.exe       C:\WINDOWS\System32\OpenSSH\scp.exe
sftp.exe      C:\WINDOWS\System32\OpenSSH\sftp.exe
ssh-agent.exe C:\WINDOWS\System32\OpenSSH\ssh-agent.exe
ssh-add.exe   C:\WINDOWS\System32\OpenSSH\ssh-add.exe
```

Missing password-oriented CLI helpers:

```text
sshpass: not found
plink: not found
pscp: not found
```

SSH agent state:

```text
ssh-add -l
exit=1
Error connecting to agent: No such file or directory
```

Environment secret channel:

```text
Get-ChildItem Env: | Where-Object { $_.Name -match 'SSH|AUTODL|PASS|TOKEN|KEY' }
exit=0
result=no matching environment variable names
```

Python SSH library availability:

```text
paramiko=True
pexpect=True
fabric=False
```

`paramiko` is available, but no password or key is available to the local
process through a non-logged channel. Embedding the AutoDL password in a shell
command, generated script, committed file, or audit artifact would create a
credential record and is therefore not used for this gate.

## Smoke Execution State

No replay was run in this audit. No `camp_selection_log.json` was produced, so
the clean-log validator still has no real DP-native selection log input.

```text
camp_selection_log_produced=False
clean_log_validator_run=False
replay_executed=False
candidate_generation_executed=False
outcome_label_generation_authorized=False
camp_retraining_authorized=False
training_execution_authorized=False
online_selector_promotion_authorized=False
atom_promotion_authorized=False
dp_modification_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

## Minimal Credential-Safe Continuation

One of these credential channels is required before the previously documented
minimal AutoDL smoke can execute from this local Codex session:

```text
option_1=start ssh-agent and add an AutoDL key usable by ssh BatchMode
option_2=pre-set a local process environment variable for a one-shot paramiko runner outside the chat transcript
option_3=run the documented AutoDL command inside an already authenticated AutoDL terminal and return the artifact paths/SHA
```

After a credential channel exists, the next execution must remain the same
minimal nonformal scope:

```text
must_enable=--camp_candidate_tensor_provenance_logging
must_not_enable=--camp_collect_closed_loop_outcomes
must_not_enable=reference_blend
must_not_enable=guidance
must_not_run=Full36
must_not_run=formal seeds 11/12/13
must_not_train=CAMP
must_not_modify=Diffusion-Planner
must_not_promote=selector/atom
must_not_claim=safety or CAMP-over-DP
```

## Decision

```text
status=credential_channel_required
user_authorization_satisfied=True
local_replay_assets_available=False
noninteractive_autodl_ssh_available=False
credential_safe_password_channel_available=False
paramiko_available=True
camp_selection_log_produced=False
clean_log_validator_run=False
```

## Next Gate

`dp_native_clean_training_log_collection_smoke_credential_channel_user_action_required`

This gate requires a credential-safe AutoDL access channel before Codex can run
the minimal nonformal smoke. It must not change DP, run Full36/formal seeds,
enable reference blend/guidance/closed-loop outcomes, retrain CAMP, promote
selectors or atoms, or make safety/CAMP-over-DP claims.
