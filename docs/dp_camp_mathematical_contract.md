# DP-Compatible CAMP Mathematical Contract

This document defines the mathematical conditions that every Diffusion
Planner CAMP atom, training change, and fallback policy must preserve.

## Candidate-Set Formulation

At one simulator tick, Diffusion Planner first produces a finite candidate
set \(\mathcal{Y}_i = \{y_{ij}\}_{j=1}^{K}\). CAMP evaluates every candidate
before solving the outer weight problem:

\[
a_{ij} = A(\xi_i, y_{ij}) \in \mathbb{R}_{+}^{R}.
\]

After extraction, \(a_{ij}\) is fixed data. CAMP does not jointly optimize
the DP trajectory and the atom weights. Therefore an atom does not need to
be convex as a function of trajectory coordinates in this finite-candidate
integration. It must satisfy the admissibility conditions below.

For simplex weights

\[
\Delta_R = \{w \in \mathbb{R}^{R}: w \ge 0,\ \mathbf{1}^{T}w = 1\},
\]

the candidate score is affine in the master variable:

\[
c_{ij}(w) = a_{ij}^{T}w.
\]

## Robust Margin Loss

Let \(o_i\) be the feasible outcome-oracle candidate and \(m_{ij} \ge 0\) the
clipped outcome margin. The per-scene ranking violation is

\[
\ell_i(w) =
\max\left(
0,
\max_{j \in \mathcal{F}_i}
\left[m_{ij} + (a_{io_i} - a_{ij})^{T}w\right]
\right).
\]

Each inner term is affine in \(w\), so \(\ell_i\) is convex and piecewise
linear. The cutting-plane algorithm adds the currently active affine piece.
Because the candidate set is finite, adding violated pieces terminates at the
exact epigraph after at most the number of feasible candidate pieces per
scene, subject to numerical solver tolerance.

Every generated inequality is globally valid: it is one affine member of the
finite maximum defining \(\ell_i\), not a local approximation. A checkpoint is
deployable only when the separation oracle certifies that the maximum omitted
piece exceeds the solved epigraph value by no more than the declared
tolerance. Exhausting iterations or merely failing to discover a new cut is
not a convergence certificate.

The Static v8 master minimizes empirical mean or CVaR of these nonnegative
losses plus convex L2 regularization over \(\Delta_R\). Its feasible set is
convex, the CVaR epigraph is convex, and the complete master is a convex
optimization problem.

## Atom Admissibility

Every deployed DP-compatible atom must:

1. Be computed from information available at the current planning tick and
   from the candidate trajectory. Closed-loop outcome labels are forbidden as
   online inputs.
2. Be fully evaluated before the outer master and treated as constant with
   respect to \(w\).
3. Return one finite scalar per candidate with a declared direction. Current
   CAMP atoms are nonnegative costs, so a larger value must never mean a
   better candidate.
4. Use a strictly positive scale fitted only on training groups. Validation
   and formal evaluation data must not influence atom scaling.
5. Be deterministic for fixed scene, candidate, simulator configuration, and
   numerical tolerance.
6. Preserve the affine score \(a_{ij}^{T}w\). An atom may not depend on
   learned CAMP weights, candidate rank, or the selected candidate.
7. Carry a stable schema version and ordered atom names. Formal training must
   reject a log whose schema is missing or differs from the checkpoint schema;
   matching dimensionality alone is not sufficient.

Robust v8 scale artifacts are self-describing and carry the same schema
metadata. The runtime accepts legacy scale arrays for backward compatibility,
but rejects a structured artifact whose version or ordered names differ from
the canonical schema.

`planned_red_light_cost` is admissible because it is the nonnegative magnitude
of the online DP red-light penalty computed for each candidate before
selection. `planned_lateral_acceleration_cost` is admissible because it is a
deterministic kinematic cost computed directly from each candidate trajectory.

## Continuous-Trajectory Extension

If a future CAMP version jointly optimizes trajectory \(y\) rather than
selecting from a fixed DP candidate set, the finite-candidate argument no
longer applies. Then each weighted atom must be convex in the lower-level
trajectory variables, or the lower-level value function must otherwise be
proven convex and provide valid subgradients. Nonconvex simulation checks,
discrete traffic rules, or learned black-box scores cannot be inserted into a
classical Benders subproblem without a different decomposition and proof.

## Feasibility And Fallback

Hard feasibility is evaluated before CAMP scoring. If at least one candidate
is feasible, infeasible candidates receive infinite selection cost and no
fallback policy may alter that branch.

All-infeasible fallback is an operational recovery policy separate from the
normal feasible-branch master. It may use its own finite-candidate convex
robust-margin master by treating all \(K\) recovery candidates as the fallback
choice set. Its atom scales and simplex weights must be trained and validated
independently, and deployment may invoke them only when the normal feasible
set is empty. `uniform` and learned fallback remain separate ablations.
Fallback outcomes cannot be used to claim that the normal feasible-branch
problem has improved.

Optional static atom-weight floors remain convex when declared before solving:
\(w_r \ge \underline{w}_r \ge 0\) and
\(\sum_r \underline{w}_r \le 1\). The implementation parameterizes
\(w=\underline{w}+(1-\mathbf{1}^\top\underline{w})z\), where
\(z\ge0\) and \(\mathbf{1}^\top z=1\). Candidate scores remain affine in the
master variable, so every finite-candidate cut remains globally valid. Floors
must be selected using training/validation evidence and recorded in the
checkpoint summary; post-training weight editing is not certified.

## Full-Horizon Safety Override

The full-horizon red-light shadow and fixed-candidate PerfectTracker rollout
diagnostics may be used only as current-tick finite-candidate data unless a
separate continuous-trajectory proof is supplied. Let \(F\) be the existing
base-feasible candidate set, \(b\in F\) be the candidate selected by the
unchanged CAMP score, and let

\[
R_k=\max(r^{30}_k,r^{80}_k)
\]

be the nonnegative union red-light certificate for candidate \(k\). Let
\(p_k\) denote the current DP progress reward, \(d^H_k\) the fixed-candidate
PerfectTracker open-loop distance over horizon \(H\), \(j^H_k\) the
corresponding mean vector jerk magnitude, and \(\ell^H_k\) the corresponding
lateral acceleration magnitude. These quantities are admissible for an
online preselection rule only if they are computed before selection from the
current tick's candidate trajectories, map, route, traffic-light state, and
tracker state. Future closed-loop outcomes and future DP replanning outputs
are forbidden.

A certified safety override must keep the unchanged CAMP candidate unless the
current candidate has positive union-red exposure and a strictly lower-risk
base-feasible candidate exists. For declared nonnegative budgets
\(\epsilon_p(x,b)\), \(\epsilon_d(x,b)\), and declared absolute comfort caps
\(\bar j(x,b)\), \(\bar \ell(x,b)\), define

\[
S_b=\{k\in F:
R_k < R_b,\;
p_k \ge p_b-\epsilon_p(x,b),\;
d^H_k \ge d^H_b-\epsilon_d(x,b),\;
j^H_k \le \bar j(x,b),\;
\ell^H_k \le \bar \ell(x,b)\}.
\]

The deployed rule is:

1. if \(F\) is empty, use the existing all-infeasible fallback path;
2. if \(R_b=0\), return \(b\);
3. if \(S_b\) is empty, return \(b\);
4. otherwise choose deterministically from \(S_b\) by minimum \(R_k\), then
   original CAMP score \(a_k^\top w\), then candidate index.

This construction is fail-closed and nonempty because the baseline candidate
is retained whenever the strict safety-override set is empty. Whenever it
does override, it proves \(R_{k^*}<R_b\) for the fixed current candidate set
and preserves the declared progress, distance, and comfort budgets. It does
not prove that future Diffusion Planner replanning, future candidate pools, or
closed-loop scene evolution will improve. Those claims require a matched
closed-loop simulator matrix.

The budgets and comfort caps are part of the rule definition, not learned
post-hoc from formal evaluation. A budget may depend on current state
\(x\), the baseline \(b\), simulator time step, speed, stopping envelope, or
published vehicle comfort limits, but it must be declared before running the
paired pilot and audited from the selection log. If a jerk cap has no
specification-backed value, jerk must remain a reported tradeoff rather than
a hard industrial guarantee.

The override is a finite-candidate selector. It leaves the robust
simplex/CVaR/L2 master unchanged and does not add a Benders subproblem. If
\(R_k\), \(d^H_k\), \(j^H_k\), or \(\ell^H_k\) are later promoted to atoms,
their logged values are fixed candidate constants in \(a_k^\top w\), so the
master remains affine in \(w\). No global convexity in trajectory coordinates
is implied by this finite-candidate argument.

There is also an impossibility condition. If
\(\{k\in F:R_k<R_b\}=\emptyset\), then no selector that only reorders or
filters the current base-feasible candidate set can strictly reduce the
union-red certificate at that tick. Repairing such a case requires changing
candidate generation, hard feasibility, horizon construction, fallback
policy, or the upstream planner/simulator configuration. It cannot be claimed
as a CAMP selector improvement.

## Underprogress Relaxation Candidate Set

The `dp_underprogress` gate is an external replay feasibility filter derived
from DP progress reward, not a CAMP atom and not a constraint in the convex
robust-margin master. Relaxing it changes the finite candidate set that CAMP
is allowed to select from. Therefore any deployed relaxation must be treated
as a new selector contract and evaluated separately from the saved CAMP weight
certificate.

Let \(q_k\) be the finite set of logged infeasibility reasons for candidate
\(k\). Split the reasons into:

- hard reasons \(q^{hard}_k\), including collision, dynamic OBB collision,
  road-border, lane-crossing, static-collision, kinematic, speed, context
  lane/speed, and DP red-light violations;
- the single soft progress reason \(u=\texttt{dp\_underprogress}\).

No hard reason may be relaxed by this rule. Define the hard-clean set

\[
G=\{k:q^{hard}_k=\emptyset\},
\]

and the original base-feasible set

\[
F=\{k:q_k=\emptyset\}.
\]

The underprogress-relaxed set may only use candidates in \(G\setminus F\)
whose only logged blocker is `dp_underprogress`. If \(F\) is empty, the
existing all-infeasible fallback path remains responsible; underprogress
relaxation must not create a separate fallback branch.

Given the unchanged CAMP-selected baseline \(b\in F\), the default-off
underprogress relaxation is allowed to form a candidate set only when all
of the following are true:

1. \(R_b>0\);
2. no base-feasible safety override has already selected a lower-risk
   candidate under the declared full-horizon override contract;
3. a candidate \(k\in G\setminus F\) has \(q_k=\{u\}\);
4. \(R_k<R_b\);
5. \(p_k \ge p_b-\epsilon^u_p(x,b)\);
6. \(d^H_k \ge d^H_b-\epsilon^u_d(x,b)\);
7. the red stopping-margin cost is nonworse than the baseline;
8. all declared absolute comfort caps hold, including the H-step lateral cap;
9. every budget and cap was declared before the paired pilot.

For a declared set of nonnegative budgets, define

\[
U_b=\{k\in G\setminus F:
q_k=\{u\},\;
R_k<R_b,\;
p_k \ge p_b-\epsilon^u_p(x,b),\;
d^H_k \ge d^H_b-\epsilon^u_d(x,b),\;
s_k \le s_b,\;
\ell^H_k \le \bar\ell^u(x,b)\}.
\]

Here \(s_k\) is the current-tick red stopping-margin cost. If a
specification-backed jerk cap is available, it may be added as
\(j^H_k \le \bar j^u(x,b)\); otherwise jerk remains an audited tradeoff and
cannot be claimed as a hard comfort guarantee.

The deployed rule must be fail-closed:

1. if \(F\) is empty, use the existing all-infeasible fallback path;
2. compute the ordinary CAMP baseline \(b\in F\);
3. if \(R_b=0\), return \(b\);
4. if the base-feasible safety override succeeds, use it;
5. if \(U_b\) is empty, return \(b\);
6. otherwise choose deterministically from \(U_b\) by minimum \(R_k\), then
   minimum stopping-margin cost \(s_k\), then original unmasked CAMP affine
   score \(a_k^\top w\), then candidate index.

This rule proves only a fixed-current-candidate statement: when it changes
the selection, the chosen candidate is hard-clean, was blocked only by
`dp_underprogress`, has lower union-red exposure than the unchanged baseline,
and satisfies the declared progress, distance, stopping-margin, and comfort
budgets. It does not prove future closed-loop safety or future replanning
improvement.

Mathematically, underprogress relaxation is not Benders and does not modify
the simplex/CVaR/L2 master. For any fixed admitted finite candidate set, the
CAMP score remains affine in \(w\), and a future training run over that fixed
contract would still have a convex finite-candidate robust-margin master.
However, the existing checkpoint certificate cannot be reused to certify the
changed feasible-set contract; the logs, schema/metadata, paired pilot, and
formal evaluation gates must explicitly record that relaxation was enabled.

## Required Gates

Before an atom or training change reaches formal evaluation, it must pass:

- finite and nonnegative atom checks;
- exact atom schema version and ordered-name checks;
- simplex and affine-score checks;
- numerical convexity checks for the finite-candidate ranking loss;
- cutting-plane convergence and master-gap checks;
- grouped train/validation separation with train-only normalization;
- online-input provenance checks excluding closed-loop labels;
- fallback isolation tests;
- matched closed-loop evaluation against DP Top-1, Uniform, and the prior
  frozen CAMP checkpoint.
