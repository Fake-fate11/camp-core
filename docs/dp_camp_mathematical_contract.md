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

All-infeasible fallback is an operational recovery policy outside the convex
training master. `uniform` and `learned` fallback must therefore be reported
as separate ablations. Fallback outcomes cannot be used to claim that the
normal feasible-branch Benders problem has improved.

## Required Gates

Before an atom or training change reaches formal evaluation, it must pass:

- finite and nonnegative atom checks;
- simplex and affine-score checks;
- numerical convexity checks for the finite-candidate ranking loss;
- cutting-plane convergence and master-gap checks;
- grouped train/validation separation with train-only normalization;
- online-input provenance checks excluding closed-loop labels;
- fallback isolation tests;
- matched closed-loop evaluation against DP Top-1, Uniform, and the prior
  frozen CAMP checkpoint.
