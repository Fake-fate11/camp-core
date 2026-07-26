# V25 Industrial Evaluation v1 to v2 Migration Matrix

| v1 construct | v2 correction | Decision effect |
|---|---|---|
| 56 endpoint rows | 56 parent/family rows plus 161 exact scalar leaves | Parents are navigation only; leaves are the complete machine vector |
| grouped clearance/TTC/closing/DRAC exposure | one leaf per threshold and duration/episode statistic | Threshold removal/addition or relabeling fails closed |
| grouped speed sensitivities | eight tolerance-specific leaves | Each duration and magnitude-duration has exact units/direction |
| grouped acceleration and jerk summaries | per-axis statistic, percentile, and sensitivity-duration leaves | No hidden comfort-proxy scalar |
| grouped latency stage summaries | five leaves per stage | mean/median/p95/p99/max independently registered |
| grouped hypothetical budgets | rate and maximum-overrun leaves at 50/100/200/500/1000 ms | No budget can be silently added or removed |
| broad source strings and globs | exact sealed root/review root, inventory entry SHA, JSON pointer, shape, units, prerequisites, transform inputs | Capability becomes a sealed-evidence audit |
| collision impact relative-speed proxy marked missing | collision-onset relative-closing-speed kinematic proxy reconstructed | Proxy available; delta-v/contact severity remain missing |
| future multiplicity placeholder | exact Holm step-down families, alpha 0.05, one/two-sided CI, layered IUT, exact-zero B/T/W ties | Method fixed; numeric margins still require future preregistration |
| SafetyCost weighted sum | immutable legacy exploratory diagnostic only | Never primary, PASS, claim, training support, or adaptation evidence |

No old number, root, CAS entry, model, weight, atom, scale, selector, split, or
claim rule is changed. The v1 artifacts remain preserved diagnostics.
