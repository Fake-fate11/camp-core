"""JAXopt projected-gradient restricted masters for V26 multi-cut Benders.

The minimized function is the negative of the exact smooth convex dual.  The
coupled gamma constraints use the existing active-face capped-simplex
projection, ported operation-for-operation to JAX float64.  JAXopt owns the
line search and convergence status.  Its native ``maxiter`` boundary is also
used as a scheduling boundary for exact full-K separation.  The full-data
academic path may instead save the best primal-feasible incumbent after its
fixed patience rule and one exact zero-unseen full-K check; solver-native
completion remains an optional stronger terminal path.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np


@dataclass
class _State:
    key: tuple[str, ...]
    z_numpy: np.ndarray
    z: Any
    atoms: Any
    offsets: Any
    feasible: Any
    row_basis: Any
    null_basis: Any
    c0: Any
    active: np.ndarray
    initial_candidate: np.ndarray
    rank: int
    svd_seconds: float
    objective_kind: str
    deployment_candidate_count: int
    scene_group_indices: np.ndarray
    record_weights: np.ndarray


def _make_state(
    pattern: Any,
    *,
    bt_weights: np.ndarray,
    resume_theta: Sequence[np.ndarray],
    structured_ranking: bool,
    jax: Any,
    jnp: Any,
) -> _State:
    import scipy.linalg

    embedding = np.asarray(pattern.embeddings, dtype=np.float64)
    z_numpy = np.concatenate(
        [embedding, np.ones((embedding.shape[0], 1), dtype=np.float64)], axis=1
    )
    started = time.monotonic()
    full = bool(z_numpy.shape[0] < z_numpy.shape[1])
    _, singular, vh = scipy.linalg.svd(
        z_numpy,
        full_matrices=full,
        lapack_driver="gesvd",
        check_finite=True,
    )
    threshold = (
        np.finfo(np.float64).eps
        * max(z_numpy.shape)
        * (float(singular[0]) if singular.size else 0.0)
        * 32.0
    )
    rank = int(np.sum(singular > threshold))
    row_basis = np.asarray(vh[:rank].T, dtype=np.float64)
    null_basis = np.asarray(vh[rank:].T, dtype=np.float64)
    score_atoms = np.asarray(pattern.candidate_atoms, dtype=np.float64)
    if structured_ranking:
        reference_atoms = np.asarray(pattern.expert_atoms, dtype=np.float64)
        if reference_atoms.shape != (score_atoms.shape[0], score_atoms.shape[2]):
            raise ValueError("structured reference atoms must have shape [N,Q]")
        candidate_faces = reference_atoms[:, None, :] - score_atoms
        configured_face_scales = getattr(pattern, "candidate_face_scales", None)
        candidate_face_scales = (
            np.ones(score_atoms.shape[:2], dtype=np.float64)
            if configured_face_scales is None
            else np.asarray(configured_face_scales, dtype=np.float64)
        )
        if (
            candidate_face_scales.shape != score_atoms.shape[:2]
            or not np.all(np.isfinite(candidate_face_scales))
            or np.any(candidate_face_scales < 0.0)
        ):
            raise ValueError("structured candidate face scales must be finite and nonnegative")
        candidate_faces = candidate_faces * candidate_face_scales[:, :, None]
        zero_face = np.zeros((score_atoms.shape[0], 1, score_atoms.shape[2]))
        atoms_numpy = np.concatenate((candidate_faces, zero_face), axis=1)
        configured_offsets = getattr(pattern, "candidate_offsets", None)
        candidate_offsets = (
            np.ones(score_atoms.shape[:2], dtype=np.float64)
            if configured_offsets is None
            else np.asarray(configured_offsets, dtype=np.float64)
        )
        if (
            candidate_offsets.shape != score_atoms.shape[:2]
            or not np.all(np.isfinite(candidate_offsets))
            or np.any(candidate_offsets < 0.0)
        ):
            raise ValueError("structured candidate face offsets must be finite and nonnegative")
        offsets_numpy = np.concatenate(
            (
                candidate_offsets,
                np.zeros((score_atoms.shape[0], 1), dtype=np.float64),
            ),
            axis=1,
        )
        feasible_numpy = np.ones(offsets_numpy.shape, dtype=bool)
        zero_face_index = score_atoms.shape[1]
        initial_weights = np.broadcast_to(
            np.asarray(bt_weights, dtype=np.float64),
            (score_atoms.shape[0], score_atoms.shape[2]),
        )
        initial_scores = offsets_numpy + np.einsum(
            "nkr,nr->nk", atoms_numpy, initial_weights
        )
        initial_scores = np.where(feasible_numpy, initial_scores, -np.inf)
        objective_kind = (
            "pool_delta_slack_rescaling_candidate_regret_ranking"
            if configured_face_scales is not None
            else "pool_delta_candidate_regret_ranking"
            if configured_offsets is not None
            and not np.all(candidate_offsets == 1.0)
            else "unit_margin_human_demonstration_ranking"
        )
        objective_kind = str(
            getattr(pattern, "objective_kind_override", None) or objective_kind
        )
    else:
        atoms_numpy = score_atoms
        offsets_numpy = np.zeros(score_atoms.shape[:2], dtype=np.float64)
        feasible_numpy = np.ones(score_atoms.shape[:2], dtype=bool)
        zero_face_index = None
        initial_scores = np.einsum("nkr,r->nk", atoms_numpy, bt_weights)
        objective_kind = "maximum_candidate_atom_score"
    worst = np.argmax(initial_scores, axis=1)
    active = np.zeros(initial_scores.shape, dtype=bool)
    active[np.arange(active.shape[0]), worst] = True
    if zero_face_index is not None:
        active[:, zero_face_index] = True
    initial_candidate = worst
    for theta in resume_theta:
        theta_array = np.asarray(theta, dtype=np.float64)
        if theta_array.shape != (atoms_numpy.shape[2], z_numpy.shape[1]):
            raise ValueError("resume Theta shape differs from the current pattern")
        weights = z_numpy @ theta_array.T
        if not bool(np.all(np.isfinite(weights))):
            raise ValueError("resume Theta produced nonfinite scene weights")
        resume_scores = offsets_numpy + np.einsum("nkr,nr->nk", atoms_numpy, weights)
        resume_scores = np.where(feasible_numpy, resume_scores, -np.inf)
        resume_worst = np.argmax(resume_scores, axis=1)
        active[np.arange(active.shape[0]), resume_worst] = True
        initial_candidate = resume_worst
    c0 = np.zeros(z_numpy.shape[1], dtype=np.float64)
    c0[-1] = 1.0
    pattern_groups = getattr(pattern, "scene_group_indices", None)
    pattern_record_weights = getattr(pattern, "record_weights", None)
    group_array = np.asarray(
        np.arange(z_numpy.shape[0]) if pattern_groups is None else pattern_groups,
        dtype=np.int64,
    )
    record_weight_array = np.asarray(
        np.ones(z_numpy.shape[0])
        if pattern_record_weights is None
        else pattern_record_weights,
        dtype=np.float64,
    )
    if group_array.shape != (z_numpy.shape[0],) or record_weight_array.shape != (
        z_numpy.shape[0],
    ):
        raise ValueError("scene groups and record weights must have one value per record")
    if np.any(group_array < 0) or not np.all(np.isfinite(record_weight_array)):
        raise ValueError("scene groups and record weights are invalid")
    return _State(
        key=tuple(pattern.status_pattern),
        z_numpy=z_numpy,
        z=jax.device_put(jnp.asarray(z_numpy, dtype=jnp.float64)),
        atoms=jax.device_put(jnp.asarray(atoms_numpy, dtype=jnp.float64)),
        offsets=jax.device_put(jnp.asarray(offsets_numpy, dtype=jnp.float64)),
        feasible=jax.device_put(jnp.asarray(feasible_numpy, dtype=bool)),
        row_basis=jax.device_put(jnp.asarray(row_basis, dtype=jnp.float64)),
        null_basis=jax.device_put(jnp.asarray(null_basis, dtype=jnp.float64)),
        c0=jax.device_put(jnp.asarray(c0, dtype=jnp.float64)),
        active=active,
        initial_candidate=initial_candidate,
        rank=rank,
        svd_seconds=time.monotonic() - started,
        objective_kind=objective_kind,
        deployment_candidate_count=int(score_atoms.shape[1]),
        scene_group_indices=group_array,
        record_weights=record_weight_array,
    )


def _active_candidate_cut_count(states: Sequence[_State]) -> int:
    """Count only legal (record, fixed-candidate) cuts, excluding q >= 0."""

    return sum(
        int(np.sum(state.active[:, : state.deployment_candidate_count]))
        for state in states
    )


def _row_l1_ball(v: Any, active: Any, cap: float, *, jnp: Any) -> tuple[Any, Any]:
    masked = jnp.where(active, v, -jnp.inf)
    sorted_values = jnp.sort(masked, axis=1)[:, ::-1]
    sorted_finite = jnp.where(jnp.isfinite(sorted_values), sorted_values, 0.0)
    cumulative = jnp.cumsum(sorted_finite, axis=1)
    counts = jnp.arange(1, v.shape[1] + 1, dtype=v.dtype)[None, :]
    condition = sorted_values - (cumulative - float(cap)) / counts > 0.0
    rho_index = jnp.maximum(jnp.sum(condition, axis=1) - 1, 0)
    threshold = (
        jnp.take_along_axis(cumulative, rho_index[:, None], axis=1)[:, 0]
        - float(cap)
    ) / (rho_index.astype(v.dtype) + 1.0)
    equality = jnp.where(active, jnp.maximum(v - threshold[:, None], 0.0), 0.0)
    return equality, threshold


def _project_gamma_exact(v: Any, active: Any, cap: float, *, jax: Any, jnp: Any) -> Any:
    """Finite-breakpoint active-face projection onto Gamma_C."""

    capped_values, row_threshold = _row_l1_ball(
        v, active, float(cap), jnp=jnp
    )

    def total_mass(tau: Any) -> Any:
        positive = jnp.where(active, jnp.maximum(v - tau, 0.0), 0.0)
        return jnp.sum(jnp.minimum(jnp.sum(positive, axis=1), float(cap)))

    low = jnp.min(jnp.where(active, v, jnp.inf)) - float(cap)
    breakpoints = jnp.sort(
        jnp.concatenate(
            [
                low[None],
                jnp.where(active, v, jnp.inf).reshape(-1),
                row_threshold,
            ]
        )
    )
    search_iterations = int(math.ceil(math.log2(int(breakpoints.shape[0])))) + 1

    def search_body(_: int, bracket: tuple[Any, Any]) -> tuple[Any, Any]:
        lower_index, upper_index = bracket
        middle = (lower_index + upper_index) // 2
        mass = total_mass(breakpoints[middle])
        return (
            jnp.where(mass > 1.0, middle, lower_index),
            jnp.where(mass > 1.0, upper_index, middle),
        )

    lower_index, upper_index = jax.lax.fori_loop(
        0,
        search_iterations,
        search_body,
        (
            jnp.asarray(0, dtype=jnp.int32),
            jnp.asarray(breakpoints.shape[0] - 1, dtype=jnp.int32),
        ),
    )
    probe = (breakpoints[lower_index] + breakpoints[upper_index]) / 2.0
    shifted_probe = v - probe
    positive_probe = jnp.where(
        active, jnp.maximum(shifted_probe, 0.0), 0.0
    )
    capped_probe = jnp.sum(positive_probe, axis=1) > float(cap)
    positive_uncapped = (
        active & (shifted_probe > 0.0) & (~capped_probe[:, None])
    )
    count = jnp.sum(positive_uncapped)
    capped_count = jnp.sum(capped_probe)
    safe_count = jnp.maximum(count, 1)
    affine_tau = (
        capped_count.astype(v.dtype) * float(cap)
        + jnp.sum(jnp.where(positive_uncapped, v, 0.0))
        - 1.0
    ) / safe_count.astype(v.dtype)
    plateau = (
        jnp.abs(capped_count.astype(v.dtype) * float(cap) - 1.0)
        <= jnp.finfo(v.dtype).eps * 16.0
    )
    valid_face = (count > 0) | plateau
    tau = jnp.where(count > 0, affine_tau, probe)
    shifted = v - tau
    raw_positive = jnp.where(active, jnp.maximum(shifted, 0.0), 0.0)
    capped = jnp.sum(raw_positive, axis=1) > float(cap)
    gamma = jnp.where(capped[:, None], capped_values, raw_positive)
    gamma = jnp.where(active, gamma, 0.0)
    return jnp.where(valid_face, gamma, jnp.full_like(gamma, jnp.nan))


def _project_grouped_gamma(
    v: Any,
    active: Any,
    group_record_indices: Any,
    cap: float,
    *,
    jax: Any,
    jnp: Any,
) -> Any:
    """Euclidean projection for two equal-weight records per scene.

    The feasible dual has nonnegative active masses, equal row mass for the
    two policy-state records of each scene, scene mass at most ``cap``, and
    total scene mass one.  Dykstra cycles project onto these four affine/simple
    convex sets without changing the grouped primal objective.
    """

    pairs = group_record_indices
    active_count = jnp.sum(active).astype(v.dtype)
    zeros = jnp.zeros_like(v)

    def nonnegative(value: Any) -> Any:
        return jnp.where(active, jnp.maximum(value, 0.0), 0.0)

    def equal_record_mass(value: Any) -> Any:
        left = pairs[:, 0]
        right = pairs[:, 1]
        left_active = active[left]
        right_active = active[right]
        left_count = jnp.sum(left_active, axis=1).astype(value.dtype)
        right_count = jnp.sum(right_active, axis=1).astype(value.dtype)
        difference = jnp.sum(value[left], axis=1) - jnp.sum(value[right], axis=1)
        shift = difference / (left_count + right_count)
        result = jnp.where(active, value, 0.0)
        result = result.at[left].add(-shift[:, None] * left_active)
        result = result.at[right].add(shift[:, None] * right_active)
        return jnp.where(active, result, 0.0)

    def scene_cap(value: Any) -> Any:
        left = pairs[:, 0]
        right = pairs[:, 1]
        pair_active = jnp.concatenate((active[left], active[right]), axis=1)
        pair_count = jnp.sum(pair_active, axis=1).astype(value.dtype)
        mass = jnp.sum(value[left], axis=1) + jnp.sum(value[right], axis=1)
        shift = jnp.maximum(mass - float(cap), 0.0) / pair_count
        result = jnp.where(active, value, 0.0)
        result = result.at[left].add(-shift[:, None] * active[left])
        result = result.at[right].add(-shift[:, None] * active[right])
        return jnp.where(active, result, 0.0)

    def total_mass(value: Any) -> Any:
        shift = (jnp.sum(jnp.where(active, value, 0.0)) - 1.0) / active_count
        return jnp.where(active, value - shift, 0.0)

    def project_set(
        value: Any, correction: Any, projector: Callable[[Any], Any]
    ) -> tuple[Any, Any]:
        shifted = value + correction
        projected = projector(shifted)
        return projected, shifted - projected

    def cycle(_: int, carry: tuple[Any, Any, Any, Any, Any]) -> tuple[Any, Any, Any, Any, Any]:
        value, p0, p1, p2, p3 = carry
        value, p0 = project_set(value, p0, nonnegative)
        value, p1 = project_set(value, p1, equal_record_mass)
        value, p2 = project_set(value, p2, scene_cap)
        value, p3 = project_set(value, p3, total_mass)
        return value, p0, p1, p2, p3

    projected, _, _, _, _ = jax.lax.fori_loop(
        0, 32, cycle, (jnp.where(active, v, 0.0), zeros, zeros, zeros, zeros)
    )
    return projected


def _dual_value_gradient(
    params: Mapping[str, Any],
    *,
    states: Sequence[_State],
    lambda_theta: float,
    jnp: Any,
) -> tuple[Any, dict[str, tuple[Any, ...]]]:
    dual = jnp.asarray(0.0, dtype=jnp.float64)
    gamma_gradient: list[Any] = []
    mu_gradient: list[Any] = []
    offset = 0
    for state, mu in zip(states, params["mu"]):
        count = int(state.z.shape[0])
        gamma = params["gamma"][offset : offset + count]
        offset += count
        combined = jnp.einsum("nk,nkr->nr", gamma, state.atoms) - mu
        g = combined.T @ state.z
        unconstrained = -g / (2.0 * float(lambda_theta))
        c_u = jnp.sum(unconstrained, axis=0)
        if int(state.null_basis.shape[1]):
            c_star = state.c0 + state.null_basis @ (
                state.null_basis.T @ (c_u - state.c0)
            )
        else:
            c_star = state.c0
        theta = unconstrained + (c_star - c_u)[None, :] / float(
            unconstrained.shape[0]
        )
        distance = jnp.sum((state.row_basis.T @ (c_u - state.c0)) ** 2)
        dual = dual + (
            -jnp.sum(g * g) / (4.0 * float(lambda_theta))
            + float(lambda_theta) * distance / float(g.shape[0])
        )
        weights = state.z @ theta.T
        scores = jnp.einsum("nkr,nr->nk", state.atoms, weights)
        dual = dual + jnp.sum(gamma * state.offsets)
        gamma_gradient.append(-(scores + state.offsets))
        mu_gradient.append(weights)
    return -dual, {
        "gamma": jnp.concatenate(gamma_gradient, axis=0),
        "mu": tuple(mu_gradient),
    }


def _theta_from_params(
    params: Mapping[str, Any],
    *,
    states: Sequence[_State],
    lambda_theta: float,
    jnp: Any,
) -> list[Any]:
    thetas: list[Any] = []
    offset = 0
    for state, mu in zip(states, params["mu"]):
        count = int(state.z.shape[0])
        gamma = params["gamma"][offset : offset + count]
        offset += count
        combined = jnp.einsum("nk,nkr->nr", gamma, state.atoms) - mu
        g = combined.T @ state.z
        unconstrained = -g / (2.0 * float(lambda_theta))
        c_u = jnp.sum(unconstrained, axis=0)
        if int(state.null_basis.shape[1]):
            c_star = state.c0 + state.null_basis @ (
                state.null_basis.T @ (c_u - state.c0)
            )
        else:
            c_star = state.c0
        thetas.append(
            unconstrained
            + (c_star - c_u)[None, :] / float(unconstrained.shape[0])
        )
    return thetas


def _strict_theta(
    state: _State, theta: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict[str, float | bool | str]]:
    theta = np.asarray(theta, dtype=np.float64).copy()
    epsilon = float(np.finfo(np.float64).eps)

    def closure_bound(value: np.ndarray) -> tuple[float, float]:
        c_theta = np.sum(value, axis=0)
        residual = float(np.max(np.abs(state.z_numpy @ c_theta - 1.0)))
        bound = (
            32.0
            * epsilon
            * float(state.z_numpy.shape[1] + 1)
            * (
                float(np.max(np.sum(np.abs(state.z_numpy), axis=1)))
                * float(np.sum(np.abs(c_theta)))
                + 1.0
            )
        )
        return residual, bound

    def uniform() -> np.ndarray:
        value = np.zeros_like(theta)
        value[:, -1] = 1.0 / float(value.shape[0])
        return value

    def close_affine(value: np.ndarray) -> tuple[np.ndarray, float]:
        c0 = np.zeros(value.shape[1], dtype=np.float64)
        c0[-1] = 1.0
        before = value.copy()
        c_theta = np.sum(value, axis=0)
        if int(state.null_basis.shape[1]):
            null_basis = np.asarray(state.null_basis, dtype=np.float64)
            c_star = c0 + null_basis @ (null_basis.T @ (c_theta - c0))
        else:
            c_star = c0
        value = value + (c_star - c_theta)[None, :] / float(value.shape[0])
        # This is the minimum-Frobenius-norm projection onto the original
        # training-scene affine constraint Z_p sum_r(Theta_r) = 1.  In a
        # rank-deficient pattern, retain the coefficient-nullspace component;
        # forcing sum_r(Theta_r) = c0 would change ||Theta||^2 without changing
        # any training-scene weight.  Assign only the binary64 summation
        # remainder to one row.
        value[-1] += c_star - np.sum(value, axis=0)
        return value, float(np.linalg.norm(value - before))

    fallback = False
    fallback_reason = "none"
    rho = 0.0
    affine_projection_norm = 0.0
    minimum_before_mix = math.nan
    if not bool(np.all(np.isfinite(theta))):
        fallback = True
        fallback_reason = "nonfinite_input_theta"
        theta = uniform()
    else:
        theta, affine_projection_norm = close_affine(theta)
        if not bool(np.all(np.isfinite(theta))):
            fallback = True
            fallback_reason = "nonfinite_affine_projection"
            theta = uniform()

    weights = state.z_numpy @ theta.T
    if not bool(np.all(np.isfinite(weights))):
        fallback = True
        fallback_reason = "nonfinite_recovered_weights"
        theta = uniform()
        weights = state.z_numpy @ theta.T
    minimum_before_mix = float(np.min(weights))
    if not fallback and minimum_before_mix < 0.0:
        interior = uniform()
        denominator = (
            np.longdouble(1.0) / np.longdouble(theta.shape[0])
            - np.longdouble(minimum_before_mix)
        )
        rho_long = -np.longdouble(minimum_before_mix) / denominator
        rho = float(np.nextafter(float(rho_long), 1.0))

        def mix_at(value: float) -> tuple[np.ndarray, np.ndarray]:
            mixed_theta = (1.0 - value) * theta + value * interior
            return mixed_theta, state.z_numpy @ mixed_theta.T

        theta_new, weights_new = mix_at(rho)
        if not bool(np.all(np.isfinite(weights_new))):
            theta = interior
            weights = state.z_numpy @ theta.T
            rho = 1.0
            fallback = True
            fallback_reason = "nonfinite_uniform_mix"
        elif bool(np.any(weights_new < 0.0)):
            low_bits = int(np.asarray(rho, dtype=np.float64).view(np.uint64))
            high_bits = int(np.asarray(1.0, dtype=np.float64).view(np.uint64))
            while low_bits + 1 < high_bits:
                middle_bits = (low_bits + high_bits) // 2
                middle = float(
                    np.asarray(middle_bits, dtype=np.uint64).view(np.float64)
                )
                _, middle_weights = mix_at(middle)
                if bool(np.all(middle_weights >= 0.0)):
                    high_bits = middle_bits
                else:
                    low_bits = middle_bits
            rho = float(np.asarray(high_bits, dtype=np.uint64).view(np.float64))
            theta_new, weights_new = mix_at(rho)
        if not fallback:
            if rho >= 1.0:
                theta = interior
                weights = state.z_numpy @ theta.T
                fallback = True
                fallback_reason = "nonrepresentable_uniform_mix"
            else:
                theta = theta_new
                weights = weights_new
    affine_residual, affine_bound = closure_bound(theta)
    if (
        not math.isfinite(affine_residual)
        or affine_residual > affine_bound
        or not bool(np.all(np.isfinite(weights)))
        or bool(np.any(weights < 0.0))
    ):
        fallback = True
        fallback_reason = "unrecoverable_final_feasibility"
        theta = uniform()
        weights = state.z_numpy @ theta.T
        affine_residual, affine_bound = closure_bound(theta)
    if affine_residual > affine_bound or bool(np.any(weights < 0.0)):
        raise FloatingPointError("strict primal construction failed")
    return theta, weights, {
        "uniform_fallback": fallback,
        "uniform_fallback_reason": fallback_reason,
        "uniform_mix_rho": rho,
        "affine_projection_norm": affine_projection_norm,
        "minimum_weight_before_mix": minimum_before_mix,
        "affine_closure": affine_residual,
        "affine_backward_error_bound": affine_bound,
        "minimum_weight": float(np.min(weights)),
    }


def _cvar(values: np.ndarray, alpha: float) -> float:
    ordered = np.sort(np.asarray(values, dtype=np.float64))
    index = max(int(math.ceil(float(alpha) * ordered.size)) - 1, 0)
    eta = ordered[index]
    return float(
        eta
        + np.sum(np.maximum(ordered - eta, 0.0))
        / ((1.0 - float(alpha)) * float(ordered.size))
    )


def _scene_group_average(
    values_by_state: Sequence[np.ndarray],
    states: Sequence[_State],
    scene_count: int,
) -> np.ndarray:
    grouped = np.zeros(int(scene_count), dtype=np.float64)
    for values, state in zip(values_by_state, states):
        row = np.asarray(values, dtype=np.float64)
        if row.shape != state.record_weights.shape:
            raise ValueError("one loss value is required for every policy-state record")
        np.add.at(
            grouped,
            state.scene_group_indices,
            state.record_weights * row,
        )
    return grouped


ACADEMIC_APPROXIMATE_RELATIVE_IMPROVEMENT = 0.001
ACADEMIC_APPROXIMATE_PATIENCE_BLOCKS = 100


def _advance_academic_approximate_patience(
    *,
    anchor_best: float | None,
    patience: int,
    best_full_objective: float,
    eligible: bool,
) -> tuple[float | None, int, float | None, bool]:
    """Advance the frozen academic approximate-Benders stopping state."""

    if not eligible:
        return anchor_best, patience, None, False
    if anchor_best is None:
        return float(best_full_objective), 0, None, False
    if anchor_best == 0.0:
        relative_improvement = (
            math.inf if best_full_objective < anchor_best else 0.0
        )
    else:
        relative_improvement = (
            float(anchor_best) - float(best_full_objective)
        ) / abs(float(anchor_best))
    if relative_improvement >= ACADEMIC_APPROXIMATE_RELATIVE_IMPROVEMENT:
        return float(best_full_objective), 0, relative_improvement, False
    patience += 1
    return (
        anchor_best,
        patience,
        relative_improvement,
        patience >= ACADEMIC_APPROXIMATE_PATIENCE_BLOCKS,
    )


def solve_scene_conditioned_camp_jaxopt_benders(
    patterns: Sequence[Any],
    *,
    bt_rows: Mapping[tuple[str, ...], Mapping[str, Any]],
    alpha: float,
    lambda_theta: float,
    progress: Callable[[Mapping[str, Any]], None] | None = None,
    checkpoint: Callable[
        [Mapping[str, Any], Mapping[tuple[str, ...], np.ndarray]], None
    ]
    | None = None,
    separation_observer: Callable[
        [Mapping[str, Any], Mapping[tuple[str, ...], np.ndarray]], None
    ]
    | None = None,
    resume_theta_rows: Sequence[
        Mapping[tuple[str, ...], np.ndarray]
    ] = (),
    structured_ranking: bool = False,
    grouped_scene_cvar: bool = False,
    allow_academic_approximate_completion: bool = True,
) -> tuple[dict[tuple[str, ...], np.ndarray], list[dict[str, Any]]]:
    """Run non-accelerated JAXopt PG masters and finite-K separation."""

    import jax
    import jax.numpy as jnp
    import jaxopt

    jax.config.update("jax_enable_x64", True)
    if jax.default_backend() != "gpu":
        raise RuntimeError(f"JAXopt master requires GPU, observed {jax.default_backend()}")
    total_started = time.monotonic()
    states: list[_State] = []
    last_precompute_progress = total_started
    for pattern_index, pattern in enumerate(patterns):
        state = _make_state(
            pattern,
            bt_weights=np.asarray(
                bt_rows[tuple(pattern.status_pattern)]["weights"], dtype=np.float64
            ),
            resume_theta=[
                np.asarray(row[tuple(pattern.status_pattern)], dtype=np.float64)
                for row in resume_theta_rows
            ],
            structured_ranking=bool(structured_ranking),
            jax=jax,
            jnp=jnp,
        )
        states.append(state)
        now = time.monotonic()
        if progress is not None and (
            now - last_precompute_progress >= 60.0
            or pattern_index + 1 == len(patterns)
        ):
            progress(
                {
                    "phase": "jaxopt_precompute_running",
                    "precompute_completed_patterns": pattern_index + 1,
                    "precompute_total_patterns": len(patterns),
                    "total_elapsed_seconds": now - total_started,
                    "eta_status": "unknown_until_precompute_and_first_native_master_return",
                }
            )
            last_precompute_progress = now

    total_records = sum(int(state.z_numpy.shape[0]) for state in states)
    if not grouped_scene_cvar:
        record_offset = 0
        for state in states:
            count = int(state.z_numpy.shape[0])
            state.scene_group_indices = np.arange(
                record_offset, record_offset + count, dtype=np.int64
            )
            state.record_weights = np.ones(count, dtype=np.float64)
            record_offset += count
    record_groups = (
        np.concatenate([state.scene_group_indices for state in states])
        if grouped_scene_cvar
        else np.arange(total_records, dtype=np.int64)
    )
    record_weights = (
        np.concatenate([state.record_weights for state in states])
        if grouped_scene_cvar
        else np.ones(total_records, dtype=np.float64)
    )
    total_scenes = int(np.max(record_groups)) + 1
    if set(record_groups.tolist()) != set(range(total_scenes)):
        raise ValueError("scene group indices must be contiguous")
    group_weight_sums = np.zeros(total_scenes, dtype=np.float64)
    np.add.at(group_weight_sums, record_groups, record_weights)
    if not np.allclose(group_weight_sums, 1.0, rtol=0.0, atol=1e-12):
        raise ValueError("record weights must sum to one within every scene")
    group_record_indices_numpy: np.ndarray | None = None
    if grouped_scene_cvar:
        if total_records != 2 * total_scenes or not np.all(record_weights == 0.5):
            raise ValueError("grouped scene CVaR requires exactly two equal-weight records")
        ordered = np.argsort(record_groups, kind="stable")
        grouped = record_groups[ordered].reshape(total_scenes, 2)
        if not np.all(grouped[:, 0] == grouped[:, 1]):
            raise ValueError("each grouped scene must own exactly two records")
        group_record_indices_numpy = ordered.reshape(total_scenes, 2)
    elif total_records != total_scenes or not np.all(record_weights == 1.0):
        raise ValueError("ungrouped CVaR requires one unit-weight record per scene")
    cap = 1.0 / ((1.0 - float(alpha)) * float(total_scenes))
    # The raw dual masses are O(1/N), while JAXopt's native fixed-point error
    # is an absolute Euclidean norm in the supplied parameter coordinates.
    # Use scene-density coordinates x=N*(gamma, mu) and the exactly equivalent
    # objective N^(3/2) f(x/N).  Then grad_x=sqrt(N)*grad f, the Hessian is
    # reduced by sqrt(N), and JAXopt's unchanged default tolerance measures the
    # empirical-L2-scaled raw fixed-point map.  The dual maximizer, recovered
    # Theta, and every reported CAMP objective remain unscaled and unchanged.
    internal_variable_scale = float(total_scenes)
    internal_objective_scale = float(total_scenes) ** 1.5
    native_error_amplification = math.sqrt(float(total_scenes))
    gamma_values: list[Any] = []
    mu_values: list[Any] = []
    for state in states:
        gamma = np.zeros(state.active.shape, dtype=np.float64)
        gamma[np.arange(gamma.shape[0]), state.initial_candidate] = (
            state.record_weights / float(total_scenes)
        )
        gamma_values.append(
            jax.device_put(
                jnp.asarray(
                    gamma * internal_variable_scale, dtype=jnp.float64
                )
            )
        )
        mu_values.append(
            jax.device_put(
                jnp.zeros(
                    (state.z_numpy.shape[0], state.atoms.shape[2]),
                    dtype=jnp.float64,
                )
            )
        )
    params: dict[str, Any] = {
        "gamma": jnp.concatenate(gamma_values, axis=0),
        "mu": tuple(mu_values),
    }
    group_record_indices = (
        None
        if group_record_indices_numpy is None
        else jax.device_put(jnp.asarray(group_record_indices_numpy, dtype=jnp.int32))
    )

    def unscale_params(value: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "gamma": value["gamma"] / internal_variable_scale,
            "mu": tuple(
                mu / internal_variable_scale for mu in value["mu"]
            ),
        }

    def objective(value: Mapping[str, Any]) -> tuple[Any, Any]:
        raw_value, raw_gradient = _dual_value_gradient(
            unscale_params(value),
            states=states,
            lambda_theta=float(lambda_theta),
            jnp=jnp,
        )
        return raw_value * internal_objective_scale, {
            "gamma": raw_gradient["gamma"] * native_error_amplification,
            "mu": tuple(
                gradient * native_error_amplification
                for gradient in raw_gradient["mu"]
            ),
        }

    def projection(
        value: Mapping[str, Any], active_mask: Any
    ) -> dict[str, Any]:
        return {
            "gamma": internal_variable_scale
            * (
                _project_grouped_gamma(
                    value["gamma"] / internal_variable_scale,
                    active_mask,
                    group_record_indices,
                    float(cap),
                    jax=jax,
                    jnp=jnp,
                )
                if grouped_scene_cvar
                else _project_gamma_exact(
                    value["gamma"] / internal_variable_scale,
                    active_mask,
                    float(cap),
                    jax=jax,
                    jnp=jnp,
                )
            ),
            "mu": tuple(jnp.maximum(mu, 0.0) for mu in value["mu"]),
        }

    solver = jaxopt.ProjectedGradient(
        fun=objective,
        projection=projection,
        value_and_grad=True,
        acceleration=False,
        maxls=64,
    )
    progress_chunk_iterations = 10
    native_work_block_iterations = int(solver.maxiter)

    @jax.jit
    def run_progress_chunk(
        chunk_params: Mapping[str, Any],
        chunk_state: Any,
        active_mask: Any,
    ) -> tuple[Mapping[str, Any], Any]:
        initial_iteration = chunk_state.iter_num

        def cond_fun(carry: tuple[Any, Any]) -> Any:
            _, state = carry
            within_chunk = (
                state.iter_num - initial_iteration < progress_chunk_iterations
            )
            force_first_update = state.iter_num == initial_iteration
            return within_chunk & (
                force_first_update | (state.error > float(solver.tol))
            )

        def body_fun(carry: tuple[Any, Any]) -> tuple[Any, Any]:
            value, state = carry
            step = solver.update(value, state, active_mask)
            return step.params, step.state

        return jax.lax.while_loop(
            cond_fun, body_fun, (chunk_params, chunk_state)
        )

    history: list[dict[str, Any]] = []
    best_theta: dict[tuple[str, ...], np.ndarray] | None = None
    best_full_objective = math.inf
    for resume_theta in resume_theta_rows:
        resumed_strict_theta: dict[tuple[str, ...], np.ndarray] = {}
        resumed_full_costs: list[np.ndarray] = []
        resumed_regularizer = 0.0
        for state in states:
            theta_bar, weights, _ = _strict_theta(
                state,
                np.asarray(resume_theta[state.key], dtype=np.float64),
            )
            resumed_strict_theta[state.key] = theta_bar
            resumed_regularizer += float(lambda_theta) * float(
                np.sum(theta_bar * theta_bar)
            )
            scores = np.einsum(
                "nkr,nr->nk",
                np.asarray(jax.device_get(state.atoms), dtype=np.float64),
                weights,
            ) + np.asarray(jax.device_get(state.offsets), dtype=np.float64)
            scores = np.where(
                np.asarray(jax.device_get(state.feasible), dtype=bool),
                scores,
                -np.inf,
            )
            resumed_full_costs.append(np.max(scores, axis=1))
        resumed_objective = resumed_regularizer + _cvar(
            _scene_group_average(resumed_full_costs, states, total_scenes),
            float(alpha),
        )
        if resumed_objective < best_full_objective:
            best_full_objective = resumed_objective
            best_theta = {
                key: value.copy() for key, value in resumed_strict_theta.items()
            }
    round_index = 0
    native_work_blocks_completed = 0
    native_state: Any | None = None
    approximate_anchor_best: float | None = None
    approximate_patience = 0
    approximate_final_check_armed = False
    previous_uniform_fallback = False
    while True:
        round_index += 1
        round_started = time.monotonic()
        active_mask = jax.device_put(
            jnp.asarray(np.concatenate([state.active for state in states]), dtype=bool)
        )
        if native_state is None:
            native_state = solver.init_state(params, active_mask)
        round_start_iteration = int(
            np.asarray(jax.device_get(native_state.iter_num))
        )
        previous_iteration = round_start_iteration
        master_started = time.monotonic()
        last_progress_report = master_started
        completed_chunks = 0
        while True:
            chunk_started = time.monotonic()
            params, native_state = run_progress_chunk(
                params, native_state, active_mask
            )
            native_state.error.block_until_ready()
            chunk_seconds = time.monotonic() - chunk_started
            native_iteration_total = int(
                np.asarray(jax.device_get(native_state.iter_num))
            )
            chunk_iterations = native_iteration_total - previous_iteration
            native_iterations_round = (
                native_iteration_total - round_start_iteration
            )
            previous_iteration = native_iteration_total
            native_error = float(
                np.asarray(jax.device_get(native_state.error))
            )
            native_stepsize = float(
                np.asarray(jax.device_get(native_state.stepsize))
            )
            native_objective = float(
                np.asarray(jax.device_get(objective(params)[0]))
            ) / internal_objective_scale
            if not math.isfinite(native_error):
                raise RuntimeError(
                    "JAXopt ProjectedGradient produced a nonfinite native error"
                )
            chunk_rate = chunk_iterations / max(
                chunk_seconds, np.finfo(np.float64).eps
            )
            now = time.monotonic()
            block_elapsed = now - master_started
            block_rate = native_iterations_round / max(
                block_elapsed, np.finfo(np.float64).eps
            )
            native_master_complete = native_error <= float(solver.tol)
            native_work_boundary_reached = (
                native_iterations_round >= native_work_block_iterations
            )
            remaining_to_separation = max(
                native_work_block_iterations - native_iterations_round, 0
            )
            next_separation_eta_seconds = (
                0.0
                if native_master_complete or native_work_boundary_reached
                else remaining_to_separation / block_rate
            )
            default_limit_crossings = (
                native_iteration_total // int(solver.maxiter)
            )
            completed_chunks += 1
            if native_master_complete:
                eta_status = (
                    "native_master_complete_pending_exact_full_K_separation"
                )
            elif native_work_boundary_reached:
                eta_status = (
                    "native_work_block_complete_pending_exact_full_K_separation"
                )
            else:
                eta_status = "unknown_until_native_work_boundary_or_completion"
            if progress is not None and (
                completed_chunks == 1
                or now - last_progress_report >= 60.0
                or native_master_complete
                or native_work_boundary_reached
            ):
                progress(
                    {
                        "phase": "jaxopt_master_chunk_complete",
                        "round": round_index,
                        "active_candidate_cuts": _active_candidate_cut_count(states),
                        "progress_chunk_iterations": progress_chunk_iterations,
                        "chunk_native_iterations": chunk_iterations,
                        "chunk_elapsed_seconds": chunk_seconds,
                        "native_iterations_per_second": chunk_rate,
                        "native_iteration_total": native_iteration_total,
                        "native_iterations_round": native_iterations_round,
                        "native_default_limit_crossings": default_limit_crossings,
                        "native_error": native_error,
                        "native_error_raw_coordinate_equivalent": (
                            native_error / native_error_amplification
                        ),
                        "native_error_amplification": native_error_amplification,
                        "native_stepsize": native_stepsize,
                        "native_objective": native_objective,
                        "internal_variable_scale": internal_variable_scale,
                        "internal_objective_scale": internal_objective_scale,
                        "native_default_tol": float(solver.tol),
                        "native_default_maxiter": int(solver.maxiter),
                        "native_line_search_maxls": int(solver.maxls),
                        "native_master_complete": native_master_complete,
                        "native_work_boundary_reached": (
                            native_work_boundary_reached
                        ),
                        "native_work_block_iterations": (
                            native_work_block_iterations
                        ),
                        "native_work_blocks_completed": (
                            native_work_blocks_completed
                            + int(native_work_boundary_reached)
                        ),
                        "master_elapsed_seconds": time.monotonic() - master_started,
                        "total_elapsed_seconds": time.monotonic() - total_started,
                        "eta_status": eta_status,
                        "next_separation_eta_seconds": next_separation_eta_seconds,
                        "next_separation_eta_basis": (
                            "remaining_iterations_in_current_native_work_block_"
                            "divided_by_observed_current_block_throughput"
                        ),
                        "final_eta_status": (
                            "unknown_pending_solver_native_current_master_and_exact_full_K_zero_unseen"
                            if structured_ranking
                            else "unknown_pending_zero_new_cut_and_descriptive_"
                            "stability_assessment"
                        ),
                        "final_eta_seconds_range": None,
                    }
                )
                last_progress_report = now
            if native_master_complete or native_work_boundary_reached:
                if native_work_boundary_reached:
                    native_work_blocks_completed += 1
                if native_master_complete:
                    native_status = (
                        "jaxopt_default_convergence_error_at_or_below_native_tol"
                    )
                else:
                    native_status = (
                        "jaxopt_native_maxiter_work_boundary_approximate_iterate"
                    )
                break

        master_seconds = time.monotonic() - master_started
        theta_devices = _theta_from_params(
            unscale_params(params),
            states=states,
            lambda_theta=float(lambda_theta),
            jnp=jnp,
        )
        theta_arrays = [
            np.asarray(jax.device_get(theta), dtype=np.float64)
            for theta in theta_devices
        ]
        strict_theta: dict[tuple[str, ...], np.ndarray] = {}
        full_cost_parts: list[np.ndarray] = []
        restricted_cost_parts: list[np.ndarray] = []
        worst_indices: list[np.ndarray] = []
        maximum_simplex_error = 0.0
        maximum_simplex_bound = 0.0
        minimum_weight = math.inf
        regularizer = 0.0
        uniform_fallback_pattern_indices: list[int] = []
        uniform_fallback_affected_scenes = 0
        uniform_mixed_pattern_indices: list[int] = []
        maximum_uniform_mix_rho = 0.0
        maximum_affine_projection_norm = 0.0
        separation_started = time.monotonic()
        for pattern_index, (state, theta) in enumerate(zip(states, theta_arrays)):
            theta_bar, _, feasible = _strict_theta(state, theta)
            strict_theta[state.key] = theta_bar
            if bool(feasible["uniform_fallback"]):
                uniform_fallback_pattern_indices.append(pattern_index)
                uniform_fallback_affected_scenes += int(state.z_numpy.shape[0])
            rho = float(feasible["uniform_mix_rho"])
            if rho > 0.0:
                uniform_mixed_pattern_indices.append(pattern_index)
            maximum_uniform_mix_rho = max(maximum_uniform_mix_rho, rho)
            maximum_affine_projection_norm = max(
                maximum_affine_projection_norm,
                float(feasible["affine_projection_norm"]),
            )
            maximum_simplex_error = max(
                maximum_simplex_error, float(feasible["affine_closure"])
            )
            maximum_simplex_bound = max(
                maximum_simplex_bound,
                float(feasible["affine_backward_error_bound"]),
            )
            minimum_weight = min(
                minimum_weight, float(feasible["minimum_weight"])
            )
            regularizer += float(lambda_theta) * float(np.sum(theta_bar * theta_bar))
            weights_device = state.z @ jnp.asarray(theta_bar, dtype=jnp.float64).T
            scores = state.offsets + jnp.einsum(
                "nkr,nr->nk", state.atoms, weights_device
            )
            scores = jnp.where(state.feasible, scores, -jnp.inf)
            full_cost = jnp.max(scores, axis=1)
            restricted_cost = jnp.max(
                jnp.where(jnp.asarray(state.active), scores, -jnp.inf), axis=1
            )
            worst = jnp.argmax(scores, axis=1)
            full_cost_parts.append(
                np.asarray(jax.device_get(full_cost), dtype=np.float64)
            )
            restricted_cost_parts.append(
                np.asarray(jax.device_get(restricted_cost), dtype=np.float64)
            )
            worst_indices.append(
                np.asarray(jax.device_get(worst), dtype=np.int64)
            )
        separation_seconds = time.monotonic() - separation_started
        full_cvar = _cvar(
            _scene_group_average(full_cost_parts, states, total_scenes),
            float(alpha),
        )
        restricted_cvar = _cvar(
            _scene_group_average(restricted_cost_parts, states, total_scenes),
            float(alpha),
        )
        full_objective = regularizer + full_cvar
        restricted_objective = regularizer + restricted_cvar
        if full_objective < best_full_objective:
            best_full_objective = full_objective
            best_theta = {
                key: value.copy() for key, value in strict_theta.items()
            }
        assert best_theta is not None

        current_iterate_new_cuts = 0
        for state, worst in zip(states, worst_indices):
            rows = np.arange(state.active.shape[0])
            missing = ~state.active[rows, worst]
            current_iterate_new_cuts += int(np.sum(missing))
            state.active[rows[missing], worst[missing]] = True
        current_iterate_zero_new_cut_pass = current_iterate_new_cuts == 0

        uniform_fallback = bool(uniform_fallback_pattern_indices)
        recovery_transition = previous_uniform_fallback and not uniform_fallback
        strict_feasible = True
        # Every recovered best incumbent is primal feasible.  Uniform recovery
        # and recovery transitions remain diagnostics; they do not create an
        # extra patience window or block the academic approximate rule.
        approximate_eligible = strict_feasible
        (
            approximate_anchor_best,
            approximate_patience,
            anchor_relative_improvement,
            patience_reached,
        ) = _advance_academic_approximate_patience(
            anchor_best=approximate_anchor_best,
            patience=approximate_patience,
            best_full_objective=best_full_objective,
            eligible=approximate_eligible,
        )
        approximate_final_check_armed = bool(
            allow_academic_approximate_completion
            and (approximate_final_check_armed or patience_reached)
        )

        best_checkpoint_new_cuts: int | None = None
        best_checkpoint_full_objective: float | None = None
        best_checkpoint_separation_seconds: float | None = None
        if approximate_final_check_armed:
            best_check_started = time.monotonic()
            best_cost_parts: list[np.ndarray] = []
            best_regularizer = 0.0
            best_checkpoint_new_cuts = 0
            for state in states:
                theta = np.asarray(best_theta[state.key], dtype=np.float64)
                best_regularizer += float(lambda_theta) * float(
                    np.sum(theta * theta)
                )
                best_weights = state.z @ jnp.asarray(
                    theta, dtype=jnp.float64
                ).T
                best_scores = state.offsets + jnp.einsum(
                    "nkr,nr->nk", state.atoms, best_weights
                )
                best_scores = jnp.where(state.feasible, best_scores, -jnp.inf)
                best_cost_parts.append(
                    np.asarray(
                        jax.device_get(jnp.max(best_scores, axis=1)),
                        dtype=np.float64,
                    )
                )
                best_worst = np.asarray(
                    jax.device_get(jnp.argmax(best_scores, axis=1)),
                    dtype=np.int64,
                )
                rows = np.arange(state.active.shape[0])
                missing = ~state.active[rows, best_worst]
                best_checkpoint_new_cuts += int(np.sum(missing))
                state.active[rows[missing], best_worst[missing]] = True
            best_checkpoint_full_objective = best_regularizer + _cvar(
                _scene_group_average(best_cost_parts, states, total_scenes),
                float(alpha),
            )
            best_checkpoint_separation_seconds = (
                time.monotonic() - best_check_started
            )
            if best_checkpoint_new_cuts > 0:
                approximate_final_check_armed = False
                approximate_patience = 0
                approximate_anchor_best = float(best_full_objective)

        active_cuts = _active_candidate_cut_count(states)
        new_cuts = current_iterate_new_cuts + int(
            best_checkpoint_new_cuts or 0
        )
        approximate_terminal_completion = (
            approximate_final_check_armed
            and best_checkpoint_new_cuts == 0
        )
        solver_native_terminal_completion = (
            native_master_complete and current_iterate_zero_new_cut_pass
        )
        terminal_completion = (
            approximate_terminal_completion
            or solver_native_terminal_completion
        )
        previous_uniform_fallback = uniform_fallback
        round_seconds = time.monotonic() - round_started
        previous_durations = [float(row["round_elapsed_seconds"]) for row in history]
        typical_round = float(np.median(previous_durations + [round_seconds]))
        row = {
            "outer_step": round_index,
            "solver_status": native_status,
            "solver_success": native_master_complete,
            "master_native_complete": native_master_complete,
            "separation_iterate_status": (
                "solver_native_complete"
                if native_master_complete
                else "approximate_restricted_master_work_boundary"
            ),
            "native_work_block_iterations": native_work_block_iterations,
            "native_work_blocks_completed": native_work_blocks_completed,
            "native_iterations": native_iterations_round,
            "native_iteration_total": native_iteration_total,
            "native_default_limit_crossings": default_limit_crossings,
            "native_error": native_error,
            "native_error_raw_coordinate_equivalent": (
                native_error / native_error_amplification
            ),
            "native_error_amplification": native_error_amplification,
            "risk_scene_count": total_scenes,
            "policy_state_record_count": total_records,
            "records_per_scene": 2 if grouped_scene_cvar else 1,
            "scene_loss_aggregation": (
                "equal_round0_round1_average_before_CVaR"
                if grouped_scene_cvar
                else "one_record_per_scene"
            ),
            "native_stepsize": native_stepsize,
            "native_default_tol": float(solver.tol),
            "native_default_maxiter": int(solver.maxiter),
            "native_line_search_maxls": int(solver.maxls),
            "native_objective": native_objective,
            "internal_variable_scale": internal_variable_scale,
            "internal_objective_scale": internal_objective_scale,
            "restricted_objective": restricted_objective,
            "exact_full_candidate_cvar": full_cvar,
            "theta_regularization": regularizer,
            "exact_objective": full_objective,
            "best_primal_feasible_full_objective": best_full_objective,
            "new_candidate_cuts": new_cuts,
            "current_iterate_new_candidate_cuts": current_iterate_new_cuts,
            "best_checkpoint_new_candidate_cuts": best_checkpoint_new_cuts,
            "total_candidate_cuts": active_cuts,
            "zero_new_cut_pass": current_iterate_zero_new_cut_pass,
            "current_iterate_zero_new_cut_pass": (
                current_iterate_zero_new_cut_pass
            ),
            "best_checkpoint_zero_unseen_legal_cuts": (
                None
                if best_checkpoint_new_cuts is None
                else best_checkpoint_new_cuts == 0
            ),
            "best_checkpoint_exact_full_K_objective": (
                best_checkpoint_full_objective
            ),
            "best_checkpoint_separation_elapsed_seconds": (
                best_checkpoint_separation_seconds
            ),
            "strict_primal_feasible": strict_feasible,
            "recovery_transition": recovery_transition,
            "approximate_stop_eligible": approximate_eligible,
            "approximate_anchor_best_full_objective": (
                approximate_anchor_best
            ),
            "approximate_anchor_relative_cumulative_improvement": (
                anchor_relative_improvement
            ),
            "approximate_patience": approximate_patience,
            "approximate_patience_blocks": (
                ACADEMIC_APPROXIMATE_PATIENCE_BLOCKS
            ),
            "approximate_relative_improvement_reset": (
                ACADEMIC_APPROXIMATE_RELATIVE_IMPROVEMENT
            ),
            "approximate_final_check_armed": approximate_final_check_armed,
            "approximate_terminal_completion": (
                approximate_terminal_completion
            ),
            "solver_native_terminal_completion": (
                solver_native_terminal_completion
            ),
            "terminal_completion": terminal_completion,
            "completion_claim": (
                "approximate_Benders_checkpoint_not_solver_native_optimum"
                if approximate_terminal_completion
                and not solver_native_terminal_completion
                else "solver_native_master_and_exact_full_K_zero_new_cut"
                if solver_native_terminal_completion
                else "not_terminal"
            ),
            "objective_kind": states[0].objective_kind,
            "cut_identity_source": (
                "exact_full_K_argmax_demonstration_calibrated_target_set_negative_candidate_identity_with_zero_face_separate"
                if states[0].objective_kind
                == "demonstration_calibrated_target_set_structured_hinge"
                else
                "exact_full_K_argmax_pool_delta_slack_rescaling_scene_round_candidate_identity_with_q_ge_0_face_separate"
                if states[0].objective_kind == "pool_delta_slack_rescaling_candidate_regret_ranking"
                else "exact_full_K_argmax_pool_delta_scene_round_candidate_identity_with_q_ge_0_face_separate"
                if states[0].objective_kind == "pool_delta_candidate_regret_ranking"
                else "exact_full_K_argmax_unit_margin_human_demo_scene_round_candidate_identity_with_q_ge_0_face_separate"
                if structured_ranking
                else "exact_full_K_argmax_original_scene_candidate_identity"
            ),
            "simplex_error": maximum_simplex_error,
            "simplex_backward_error_bound": maximum_simplex_bound,
            "minimum_weight": minimum_weight,
            "uniform_fallback_pattern_indices": uniform_fallback_pattern_indices,
            "uniform_fallback_affected_scenes": uniform_fallback_affected_scenes,
            "uniform_mixed_pattern_indices": uniform_mixed_pattern_indices,
            "maximum_uniform_mix_rho": maximum_uniform_mix_rho,
            "maximum_affine_projection_norm": maximum_affine_projection_norm,
            "master_elapsed_seconds": master_seconds,
            "separation_device": str(jax.devices()[0]),
            "separation_elapsed_seconds": separation_seconds,
            "separation_records_per_second": total_records
            / max(separation_seconds, np.finfo(np.float64).eps),
            "separation_scenes_per_second": total_scenes
            / max(separation_seconds, np.finfo(np.float64).eps),
            "round_elapsed_seconds": round_seconds,
            "total_elapsed_seconds": time.monotonic() - total_started,
            "eta_status": (
                "complete_approximate_or_solver_native_Benders_checkpoint"
                if terminal_completion
                else "unknown_future_native_work_and_cut_extensions"
            ),
            "eta_seconds": 0.0 if terminal_completion else None,
            "next_separation_eta_seconds": 0.0,
            "next_separation_eta_basis": "current_exact_full_K_separation_complete",
            "final_eta_status": (
                "complete_approximate_or_solver_native_Benders_checkpoint"
                if terminal_completion
                else "unknown_pending_academic_patience_and_best_checkpoint_exact_separation"
            ),
            "final_eta_seconds_range": [0.0, 0.0] if terminal_completion else None,
            "typical_observed_round_seconds": typical_round,
            "heartbeat_basis": (
                "completed_native_work_blocks_and_exact_full_K_separation_durations"
            ),
        }
        history.append(row)
        if checkpoint is not None:
            checkpoint(
                {
                    "round": round_index,
                    "master_iteration": native_iteration_total,
                    "best_full_objective": best_full_objective,
                    "current_full_objective": full_objective,
                    "active_candidate_cuts": active_cuts,
                    "new_candidate_cuts": new_cuts,
                    "zero_new_cut_pass": current_iterate_zero_new_cut_pass,
                    "best_checkpoint_zero_unseen_legal_cuts": (
                        None
                        if best_checkpoint_new_cuts is None
                        else best_checkpoint_new_cuts == 0
                    ),
                    "best_checkpoint_new_candidate_cuts": (
                        best_checkpoint_new_cuts
                    ),
                    "best_checkpoint_exact_full_K_objective": (
                        best_checkpoint_full_objective
                    ),
                    "strict_primal_feasible": strict_feasible,
                    "recovery_transition": recovery_transition,
                    "approximate_stop_eligible": approximate_eligible,
                    "approximate_anchor_best_full_objective": (
                        approximate_anchor_best
                    ),
                    "approximate_anchor_relative_cumulative_improvement": (
                        anchor_relative_improvement
                    ),
                    "approximate_patience": approximate_patience,
                    "approximate_final_check_armed": (
                        approximate_final_check_armed
                    ),
                    "approximate_terminal_completion": (
                        approximate_terminal_completion
                    ),
                    "solver_native_terminal_completion": (
                        solver_native_terminal_completion
                    ),
                    "native_master_complete": native_master_complete,
                    "final_zero_new_cut_pass": bool(
                        solver_native_terminal_completion
                        or approximate_terminal_completion
                    ),
                    "terminal_completion": terminal_completion,
                    "completion_claim": row["completion_claim"],
                    "simplex_error": maximum_simplex_error,
                    "minimum_weight": minimum_weight,
                    "uniform_fallback_pattern_indices": (
                        uniform_fallback_pattern_indices
                    ),
                    "uniform_fallback_affected_scenes": (
                        uniform_fallback_affected_scenes
                    ),
                    "uniform_mixed_pattern_indices": uniform_mixed_pattern_indices,
                    "maximum_uniform_mix_rho": maximum_uniform_mix_rho,
                    "maximum_affine_projection_norm": (
                        maximum_affine_projection_norm
                    ),
                },
                best_theta,
            )
        if progress is not None:
            progress({"phase": "jaxopt_benders_round_complete", **row})
        if separation_observer is not None:
            separation_observer(row, strict_theta)
        if terminal_completion:
            return best_theta, history


__all__ = [
    "ACADEMIC_APPROXIMATE_PATIENCE_BLOCKS",
    "ACADEMIC_APPROXIMATE_RELATIVE_IMPROVEMENT",
    "_advance_academic_approximate_patience",
    "solve_scene_conditioned_camp_jaxopt_benders",
]
