# CAMP x fixed Diffusion Planner: historical evidence ladder and preliminary table

**Status:** historical / pilot evidence only. This page does not report a V26
main effect, a closed-loop safety claim, or a holdout result. It preserves the
scope of earlier work while the V26 nuPlan three-city study is rebuilt from
official raw sources.

## What the existing record supports

| Ladder level | Existing evidence | What it supports | Boundary that remains in force |
| --- | --- | --- | --- |
| A. Migration and executability | V18 real nuPlan-mini adapter, fixed-DP loader, and materializer: **22 passed**; one real case produced a finite DP input with **16 keys**. V25 same-ego single-invocation B8: candidate 0 = row 0, **320** deterministic calls, **640** selector replays, zero post-pool calls, and a **100-cluster / 19,200-tick** multiroute run. | CAMP can be integrated as a post-generation selector over fixed DP candidates without modifying DP trajectories. | This is an integration/capability result, not an endpoint or generalization result. |
| B. Bounded offline proxy | V18 **1,931** comparisons: score **72.1707** versus **65.2628** (delta **+6.9079**); B/T/W = **1,509 / 86 / 336**; log- and scene-cluster CIs were positive. Collision-free: **1.0000** versus **0.9322**; physical-feasible: **1.0000** versus **0.9213**; clearance: **1.6046** versus **1.3930**. | A bounded offline proxy signal under its original setup. | Not a closed-loop result and not a general safety claim. |
| C. Target B8 development exposure | V25 target batch8 development run: **100 clusters / 300 arms / 19,200 ticks**. Scene collision episodes: **0.03** versus **0.07**. Scene TTC rates: <=1 s **0.031** versus **0.065**; <=3 s **0.143** versus **0.206**; <=5 s **0.284** versus **0.329**. Static also showed TTC improvement. | A development capability signal for same-pool B8 selection. | The same record also contains off-road, goal-distance, and filtered lateral-jerk trade-offs; it is not a net-benefit or safety conclusion. |
| D. Negative and historical-only checks | V18 trained-14D ADE/FDE CIs: **+0.0800 / +0.1018**, both spanning zero. V22/V24 SafetyCost CIs also spanned zero. V25 legacy-B4 SafetyCost was significant, but used **7 sequential extra DP calls**. | Evidence against overstating earlier results. | Legacy B4 is historical combination evidence only and is not a fair target B8 comparison. |

## Preliminary-result presentation table

| Result family | Reportable wording | Do not write |
| --- | --- | --- |
| Offline proxy (B) | A bounded offline proxy showed higher score, collision-free rate, physical feasibility, and clearance under its original protocol. | CAMP is safer in closed loop, or any cross-dataset/general claim. |
| Development B8 exposure (C) | In a development target-B8 exposure, the Scene selector had lower reported collision-episode and TTC incidences, alongside explicit mobility and smoothness trade-offs. | A pooled treatment-effect, a safety-benefit conclusion, or a statement that all endpoints improved. |
| Negative checks (D) | Earlier 14D ADE/FDE and SafetyCost checks were inconclusive; legacy B4 is not comparable because it used seven extra sequential DP calls. | Selective reporting of only favorable historical metrics. |

## Role of V26 three-city confirmation

V26 is the confirmatory rebuild, not a relabeling of this ladder. It uses
official nuPlan raw DB/maps and outcome-independent grouped identities:

- Boston and Pittsburgh provide the training/IID grouped-validation source.
- Singapore is frozen as an entire-city OOD test before results.
- Each evaluated state will use one fixed-DP, same-ego B8 pool with eight unique
  frozen latents; native top-1 is row 0, and CAMP re-ranks only that pool with
  zero post-pool DP/model/latent/generation calls.
- The future paper reports native top-1 versus CAMP through pre-fixed ADE/FDE,
  feasibility, domain-specific safety/progress/comfort measures, latency, and
  9D/14D/group ablations. SafetyCost remains a legacy diagnostic, not a
  weighted primary score.

Until that study is complete, label every number above **historical** or
**preliminary/pilot** and keep it separate from V26 main-effect tables.
