# DP + CAMP Device Handoff

This file records the verified handoff state for continuing the Diffusion
Planner + CAMP work from another computer.

## Source repositories

### CAMP

- Repository: `https://github.com/Fake-fate11/camp-core.git`
- Branch: `main`
- Minimum DP scene-conditioned integration commit:
  `fc318c8023626e2c84f33b08ea81b04035e153e8`

```bash
git clone https://github.com/Fake-fate11/camp-core.git
cd camp-core
git checkout main
git pull --ff-only
```

### Diffusion Planner

The integration does not modify the upstream Diffusion Planner checkout.

- Repository: `https://github.com/tier4/Diffusion-Planner.git`
- Remote branch on AutoDL: `tier4-main`
- Verified commit: `7a1d33da277a1992ec474b5383a0c963c72e04e4`

```bash
git clone https://github.com/tier4/Diffusion-Planner.git
cd Diffusion-Planner
git checkout 7a1d33da277a1992ec474b5383a0c963c72e04e4
```

The active AutoDL checkout is:

```text
/root/autodl-tmp/Diffusion-Planner
```

## AutoDL connection

```bash
ssh -p 39458 root@connect.bjb2.seetacloud.com
```

The password is intentionally not stored in Git.

The active CAMP checkout is:

```text
/root/autodl-tmp/camp_core
```

## DP assets and trained CAMP weights

These files are intentionally excluded from Git and remain on AutoDL:

```text
/root/autodl-tmp/camp_dp_assets/diffusion_planner.pth
/root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json
/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl
/root/autodl-tmp/camp_dp_assets/camp_dp_scene_theta_v1_fc318c8/
```

Important checksums:

```text
4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75  diffusion_planner.pth
ee3145b68fd1e1e44e532933dfe66cfee4384fbd637382c87ab5190c66a8e268  diffusion_planner.param.json
f1ea74a728f28c117f9215ef75173692aace801dab2f0f9ef3858838c1502576  camp_dp_scene_theta.npz
951c9829a67a0fb7a6865ef7114eebc62d549db83c78325942db95f0cfdc02c8  atom_scales_dp_scene_theta.json
0d963c21851b460def65b3208e9e0a5bca85c3d9dd58d9c1a0db66d1157eb0fe  comparison.json
```

The trained checkpoint and comparison outputs are:

```text
/root/autodl-tmp/camp_dp_assets/camp_dp_scene_theta_v1_fc318c8/camp_dp_scene_theta.npz
/root/autodl-tmp/camp_dp_assets/camp_dp_scene_theta_v1_fc318c8/atom_scales_dp_scene_theta.json
/root/autodl-tmp/camp_dp_assets/camp_dp_scene_theta_v1_fc318c8/training_summary.json
/root/autodl-tmp/camp_dp_assets/camp_dp_scene_theta_v1_fc318c8/comparison.json
/root/autodl-tmp/camp_dp_assets/camp_dp_scene_theta_v1_fc318c8/comparison.md
```

The matched 200-step replay directories are:

```text
/root/autodl-tmp/camp_dp_replay_theta_collect_59_86_k8_steps200_fc318c8
/root/autodl-tmp/camp_dp_replay_theta_59_86_k8_steps200_fc318c8
```

## Monitoring

```bash
cd /root/autodl-tmp/camp_core

THETA_OUTPUT_DIR=/root/autodl-tmp/camp_dp_assets/camp_dp_scene_theta_v1_fc318c8 \
DP_PYTHON=/root/autodl-tmp/dp312_venv/bin/python \
bash scripts/integrations/monitor_diffusion_planner_theta.sh
```

## Session exporter limitation

A `codex-session-exporter` bundle contains the Codex session JSONL and thread
metadata. It does not contain:

- the CAMP Git working tree;
- the Diffusion Planner working tree;
- model weights, maps, routes, or replay outputs;
- ignored local documents such as `short_methods_results_summary.tex`;
- the locally modified `codex-session-exporter` source checkout.

Clone CAMP and Diffusion Planner separately, then import the session bundle.
Use `--target-cwd` or `--cwd-map` when the new workspace path differs.

The current local exporter checkout has three uncommitted Windows-related
changes. They are preserved in:

```text
scripts/integrations/codex_session_exporter_windows.patch
```

Apply them to a fresh exporter checkout with:

```bash
git -C codex-session-exporter apply --unidiff-zero \
  ../scripts/integrations/codex_session_exporter_windows.patch
```

## Migration verification

After cloning CAMP:

```bash
git rev-parse HEAD
git status --short --branch
```

Expected:

```text
## main...origin/main
```

`git rev-parse HEAD` and `git rev-parse origin/main` must print the same
commit. The exact hash advances as handoff documentation and experiment code
are updated.

On AutoDL:

```bash
git -C /root/autodl-tmp/camp_core rev-parse HEAD
git -C /root/autodl-tmp/camp_core status --short --branch
git -C /root/autodl-tmp/Diffusion-Planner rev-parse HEAD
git -C /root/autodl-tmp/Diffusion-Planner status --short --branch
```
