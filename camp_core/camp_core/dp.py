"""Public Python CAMP API for frozen Diffusion Planner candidates.

Loading/selecting imports no Torch, CVXPY, JAX or training code. The host passes
decision-time tensors to CAMPSelector.select; realized futures belong only in
evaluate. Training consumes already materialized, fixed preference target sets.
"""
from pathlib import Path
import json
import shutil

from camp_core.integrations.diffusion_planner_v26_selector import (
    DiffusionPlannerCAMPSelector as CAMPSelector,
    DiffusionPlannerCAMPTick as CAMPTick,
)
from camp_core.integrations.diffusion_planner_v26_camp_reranker import (
    CAMPReranker,
    V26_CAMP_ATOM_NAMES,
)

PREFERENCE_EVIDENCE_NAMES = tuple(V26_CAMP_ATOM_NAMES[i] for i in
    (0, 1, 2, 4, 6, 7, 3, 9, 10, 11, 12, 13, 14, 8, 5, 15))


def load(bundle):
    """Load Fixed/Scene weights and scales; returns a select/reset instance."""
    return CAMPSelector.from_directory(bundle)


def fit(evidence, scene_shared_mask, scales):
    """Fit the existing convex demonstration preference calibration.

    evidence is [N,1+K,16], H first, in the final offline calibration order:
    seven Safety, six Comfort, three Other attributes. All are lower-is-better
    with the existing source definitions. scales are the already fixed physical
    or train-only scales; this function does not estimate or change them.
    scene_shared_mask is [N,16] and applies identically to H and all K rows.
    """
    import numpy as np
    from camp_core.training.preference import _differences, _fit, _hessian, _nll_and_gradient
    values, mask = _scaled_evidence(evidence, scene_shared_mask, scales)
    if values.shape[1] < 2: raise ValueError('calibration requires H and at least one candidate')
    groups = (np.arange(7), np.arange(7,13), np.arange(13,16))
    initial = np.zeros(16)
    for mass, columns in zip((.5,.3,.2),groups): initial[columns] = mass/len(columns)
    difference = _differences(values,mask)
    result = _fit(difference,groups,initial)
    value, gradient = _nll_and_gradient(result.x,difference)
    return dict(beta_hat=result.x.copy(),sum_nll=value,mean_nll=value/len(values),
                sum_nll_gradient=gradient,sum_nll_hessian=_hessian(result.x,difference),
                group_mass=[float(result.x[g].sum()) for g in groups],
                optimizer_success=bool(result.success),optimizer_message=str(result.message))


def _scaled_evidence(evidence, scene_shared_mask, scales):
    import numpy as np
    values = np.asarray(evidence,dtype=np.float64)
    mask = np.asarray(scene_shared_mask,dtype=bool)
    scale = np.asarray(scales,dtype=np.float64)
    if values.ndim != 3 or values.shape[0] < 1 or values.shape[2] != 16 or mask.shape != (values.shape[0],16):
        raise ValueError('evidence [N,A,16] and a shared mask [N,16] are required')
    if scale.shape != (16,) or not np.isfinite(scale).all() or np.any(scale <= 0):
        raise ValueError('the 16 existing evidence scales must be finite and positive')
    if not np.isfinite(values.transpose(0,2,1)[mask]).all():
        raise ValueError('observed evidence must be finite for every alternative')
    return np.clip(values/scale[None,None,:],0.,10.),mask


def point_targets(candidate_evidence, scene_shared_mask, scales, beta):
    """Apply one frozen preference rule to a pool; retain exact ties only."""
    import numpy as np
    from camp_core.training.preference import _candidate_target
    values, mask = _scaled_evidence(candidate_evidence,scene_shared_mask,scales)
    beta = np.asarray(beta,dtype=np.float64)
    if beta.shape != (16,) or not np.isfinite(beta).all(): raise ValueError('beta must be finite [16]')
    # Zero below is the omitted term in a masked sum, not an imputed observation.
    return _candidate_target(np.where(mask[:,None,:],values,0.),beta)


def train(*, complete_pool_jsonl, embedding_npz, atom_scales_json,
          preference_target_npz, output_dir, expected_scenes,
          resume_theta_checkpoint=(), device='auto'):
    """Run the final demonstration-calibrated target-set CAMP trainer.

    Fixed uses the existing zero-valued context embedding; Scene uses frozen DP
    embeddings and its established embedded-Fixed initialization checkpoint.
    Both use CVaR .9, lambda 1, unit margin 1 and unchanged native/patience stops.
    This runs real training; it does not materialize or refit preference labels.
    """
    from camp_core.training.diffusion_planner import build_parser, run

    argv = ['--output-dir', str(output_dir), '--expected-scenes', str(expected_scenes),
            '--atom-scales-json', str(atom_scales_json), '--preference-target-npz',
            str(preference_target_npz), '--structured-transition-ranking',
            '--benders-device', device]
    for flag, paths in (('--complete-pool-jsonl', complete_pool_jsonl),
                        ('--embedding-npz', embedding_npz),
                        ('--resume-theta-checkpoint', resume_theta_checkpoint)):
        if isinstance(paths, (str, Path)): paths = [paths]
        for path in paths: argv += [flag, str(path)]
    return run(build_parser().parse_args(argv))


def evaluate(candidates, source):
    """Evaluate a saved pool with existing official planner_metrics (offline).

    source may contain realized futures. They are not passed to load/select.
    Returns each candidate's separate endpoint values, units and availability.
    Requires the upstream planner_metrics package in the evaluation environment.
    """
    from camp_core.evaluation.tier4 import evaluate_official
    return evaluate_official(candidates, source)


def initialize_scene(*, fixed_checkpoint, embedding_dimension, output):
    """Embed the trained Fixed solution as zero slopes plus unchanged biases."""
    import numpy as np
    source = Path(fixed_checkpoint)
    document = json.loads(source.with_suffix('.json').read_text(encoding='utf-8'))
    arrays = {}
    with np.load(source, allow_pickle=False) as data:
        for row in document['patterns']:
            key = row['theta_key']
            fixed = np.asarray(data[key], dtype=np.float64)
            if np.max(np.abs(fixed[:, :-1]), initial=0.) > 1e-12:
                raise ValueError('Fixed initialization requires zero context slopes')
            theta = np.zeros((len(fixed), embedding_dimension + 1))
            theta[:, -1] = fixed[:, -1]
            arrays[key] = theta
            suffix = key.removeprefix('theta_')
            for prefix in ('active_global_indices_', 'status_pattern_'):
                arrays[prefix+suffix] = data[prefix+suffix].copy()
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez(destination, **arrays)
    destination.with_suffix('.json').write_text(json.dumps(dict(
        source_fixed_checkpoint=str(source), embedding_dimension=embedding_dimension,
        patterns=document['patterns']), indent=2)+'\n', encoding='utf-8')
    return destination


def export(*, fixed_checkpoint, scene_checkpoint, atom_scales, transition_scales, directory):
    """Copy only deployment parameters/scales into the existing bundle layout."""
    fixed = CAMPReranker(fixed_checkpoint, atom_scales)
    scene = CAMPReranker(scene_checkpoint, atom_scales)
    if fixed.model_kind != 'fixed' or scene.model_kind != 'scene':
        raise ValueError('fixed/scene checkpoint roles do not match')
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    files = {'fixed_weight_camp.npz': fixed_checkpoint,
             'scene_conditioned_camp.npz': scene_checkpoint,
             'atom_scales.json': atom_scales, 'transition_scales.json': transition_scales}
    for name, source in files.items():
        if Path(source).resolve() != (root/name).resolve(): shutil.copyfile(source, root/name)
    load(root)
    return root


def export_fixed_cpp(*, checkpoint, atom_scales, transition_scales, path, candidate_count=8):
    """Export the existing Autoware draft's Fixed JSON layout, without ROS deps.

    Its current C++ loader checks candidate_pool_k. This export is not a claim
    that the draft's ROS atom materializer is equivalent to the Python selector.
    """
    reranker = CAMPReranker(checkpoint, atom_scales)
    if reranker.model_kind != 'fixed': raise ValueError('the existing C++ format is Fixed-only')
    if candidate_count < 1: raise ValueError('candidate_count must be positive')
    patterns = []
    for status, head in reranker._heads.items():
        weights = [0.] * len(V26_CAMP_ATOM_NAMES)
        for index, value in zip(head.active_global_indices, head.theta[:, -1]):
            weights[index] = float(value)
        patterns.append({'status': list(status), 'weights': weights})
    payload = dict(format_version=1, candidate_pool_k=candidate_count,
                   atom_names=list(V26_CAMP_ATOM_NAMES),
                   scales=[reranker.atom_scales[n] for n in V26_CAMP_ATOM_NAMES],
                   transition_scales=json.loads(Path(transition_scales).read_text(encoding='utf-8')),
                   patterns=patterns)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, allow_nan=False)+'\n',encoding='utf-8')
    return destination


def export_cpp(*, checkpoint, atom_scales, transition_scales, path, candidate_count=8):
    """Export Fixed or Scene raw affine heads for cpp/camp_online.

    Scene coefficients are NOT projected, clipped or renormalized at inference.
    Only observed atom values are scaled/clipped, exactly as in CAMPReranker.
    """
    model = CAMPReranker(checkpoint, atom_scales)
    if not isinstance(candidate_count, int) or candidate_count < 1:
        raise ValueError('candidate_count must be a positive integer')
    transition = json.loads(Path(transition_scales).read_text(encoding='utf-8'))
    transition = transition.get('transition_component_positive_q95', transition)
    patterns = [dict(status=list(status), active=list(head.active_global_indices),
                     theta=head.theta.tolist()) for status, head in model._heads.items()]
    payload = dict(format_version=2, model_kind=model.model_kind,
                   candidate_pool_k=candidate_count, theta_width=model._theta_width,
                   atom_names=list(V26_CAMP_ATOM_NAMES),
                   scales=[model.atom_scales[n] for n in V26_CAMP_ATOM_NAMES],
                   transition_scales=transition, patterns=patterns)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    return destination


__all__ = ['CAMPSelector', 'CAMPTick', 'PREFERENCE_EVIDENCE_NAMES', 'load', 'fit', 'point_targets', 'train', 'initialize_scene', 'evaluate', 'export', 'export_cpp', 'export_fixed_cpp']
