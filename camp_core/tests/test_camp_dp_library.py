import json
from pathlib import Path
import subprocess
import sys

import numpy as np

from camp_core import dp
from camp_core.integrations.diffusion_planner_v26_camp_reranker import build_camp_atom_artifact, V26_CAMP_ATOM_NAMES
from camp_core.training.preference import _differences, _nll_and_gradient


def test_variable_k_whole_pool_and_shared_mask():
    root=Path(__file__).resolve().parents[2]/'artifacts/camp_v26_k8_50k'
    selector=dp.load(root)
    statuses={n:'observed' for n in V26_CAMP_ATOM_NAMES}
    for k in (8,16,32):
        values={n:np.arange(k,dtype=float)[::-1] for n in V26_CAMP_ATOM_NAMES}
        art=build_camp_atom_artifact(values,statuses)
        candidates=np.arange(k*80*4).reshape(k,80,4)
        for model,phi in ((selector.pipeline.fixed,None),(selector.pipeline.scene,np.zeros(256))):
            selected,result=model.select_candidates(candidates,art,phi)
            assert art['K']==k and len(result.candidate_scores)==k
            assert result.selected_row==k-1
            np.testing.assert_array_equal(selected,candidates[-1])


def test_point_targets_mask_clip_and_exact_ties():
    evidence=np.ones((2,16,16));mask=np.ones((2,16),dtype=bool)
    mask[0,0]=False;evidence[0,:,0]=np.nan
    evidence[1,3,0]=0
    beta=np.zeros(16);beta[0]=1
    scores,target=dp.point_targets(evidence,mask,np.ones(16),beta)
    assert target[0].all() and target[1].sum()==1 and target[1,3]
    assert np.isnan(evidence[0,:,0]).all()
    np.testing.assert_array_equal(scores[0],np.zeros(16))


def test_calibration_reuses_sum_nll_gradient():
    rng=np.random.default_rng(4)
    evidence=rng.random((4,17,16));mask=np.ones((4,16),dtype=bool)
    mask[0,2]=False;evidence[0,:,2]=np.nan
    fitted=dp.fit(evidence,mask,np.ones(16))
    beta=fitted['beta_hat'];diff=_differences(evidence,mask)
    value,gradient=_nll_and_gradient(beta,diff)
    assert fitted['optimizer_success']
    np.testing.assert_allclose(fitted['sum_nll'],value)
    np.testing.assert_allclose(fitted['mean_nll']*4,value)
    direction=np.linspace(-1,1,16);eps=1e-6
    fd=(_nll_and_gradient(beta+eps*direction,diff)[0]-_nll_and_gradient(beta-eps*direction,diff)[0])/(2*eps)
    np.testing.assert_allclose(fd,gradient@direction,atol=1e-7)
    assert abs(beta.sum()-1)<1e-8 and beta.min()>=-1e-8
    assert beta[:7].sum()+1e-8>=beta[7:13].sum()>=beta[13:].sum()-1e-8


def test_deployment_export(tmp_path):
    root=Path(__file__).resolve().parents[2]/'artifacts/camp_v26_k8_50k'
    result=dp.export(fixed_checkpoint=root/'fixed_weight_camp.npz',scene_checkpoint=root/'scene_conditioned_camp.npz',
                     atom_scales=root/'atom_scales.json',transition_scales=root/'transition_scales.json',directory=tmp_path/'bundle')
    npz=result/'fixed_weight_camp.npz'
    assert npz.read_bytes()==(root/'fixed_weight_camp.npz').read_bytes()
    path=dp.export_fixed_cpp(checkpoint=npz,atom_scales=result/'atom_scales.json',transition_scales=result/'transition_scales.json',path=tmp_path/'fixed.json',candidate_count=16)
    payload=json.loads(path.read_text());assert payload['candidate_pool_k']==16
    assert len(payload['patterns'])==24
    # Test lazy deployment imports in a fresh interpreter, independently of
    # optional packages imported by other tests in the same pytest process.
    subprocess.run([
        sys.executable, '-c',
        "import sys; from camp_core import dp; dp.load(sys.argv[1]); "
        "assert not ({'jax', 'cvxpy', 'torch'} & sys.modules.keys())",
        str(root),
    ], check=True)


def test_real_trainer_target_set_faces_support_k16(tmp_path):
    from camp_core.training.diffusion_planner import PatternData, _apply_demonstration_preference_targets, build_parser
    candidates=np.arange(2*16*3,dtype=float).reshape(2,16,3)/100
    pattern=PatternData(status_pattern=('observed',)*3,active_global_indices=(0,1,2),
                        anchor_ids=('a','b'),embeddings=np.zeros((2,1)),candidate_atoms=candidates,
                        expert_atoms=np.zeros((2,3)),candidate_cuts=[set(),set()])
    targets=np.zeros((2,16),dtype=bool);targets[0,[1,4]]=True;targets[1]=True
    path=tmp_path/'targets.npz'
    np.savez(path,anchor_ids=np.array(['a','b']),target_set_mask=targets,beta_hat=np.ones(16)/16)
    report=_apply_demonstration_preference_targets([pattern],path,expected_scenes=2)
    np.testing.assert_allclose(pattern.expert_atoms[0],candidates[0,[1,4]].mean(0))
    assert not pattern.candidate_face_scales[1].any()  # Full-pool target has no negative face.
    assert report['scene_count']==2
    args=build_parser().parse_args(['--complete-pool-jsonl','p','--embedding-npz','e','--output-dir','o'])
    assert args.alpha==.9 and args.lambda_theta==1.
