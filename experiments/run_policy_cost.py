#!/usr/bin/env python3
"""Exact actual-policy expectations for two cheaper fixed rollout budgets."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from belief import ParticleBelief
from exact_small_graph import ExactReview
from integrate_particle_policy import integrate
from sampled_planning import choose


def selector_for(samples):
    def selector(belief,available,remaining,step,seed,method):
        action,detail=choose(belief,available,remaining,samples,belief.N,
                             seed*100000+samples+step*1000000)
        return action,dict(search=detail,simulated_reviews=detail['simulated_reviews'])
    return selector


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    inputs=[Path('runs/small-graph-conditioned-v1/cases.json'),Path('runs/exact-particle-policy-v1/cases.json')]
    for p in inputs:
        m=json.loads(p.with_name('manifest.json').read_text())
        if hashlib.sha256(p.read_bytes()).hexdigest()!=m['output_sha256']['cases.json']:
            raise ValueError('input hash mismatch')
    cases={(c['seed'],c['profile']):c for c in json.loads(inputs[0].read_text()) if c['budget']==3}
    references=json.loads(inputs[1].read_text())
    args.out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).parent
    names=['run_policy_cost.py','integrate_particle_policy.py','sampled_planning.py',
           'belief.py','exact_small_graph.py','run_full_episode_guard.py',
           'validate_selection_guard.py','POLICY_COST_PROTOCOL.md']
    manifest=dict(status='in_progress',samples=[64,256],particles=1024,seeds=list(range(4)),
                  input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
                  source_sha256={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names})
    def save():
        (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    save();rows=[]
    for reference in references:
        c=cases[reference['graph'],reference['profile']];seed=reference['seed']
        prior=c['conditioned_prior'] if c['profile']=='normal-confidence' else c['type_prior']
        env=ExactReview(c['parents'],prior,sinks=c['sinks'])
        edges={(p,i):.6 for i,ps in enumerate(c['parents']) for p in ps}
        belief=ParticleBelief(c['parents'],range(6),c['sinks'],edges,prior,.9,1024,seed+50000)
        for samples in manifest['samples']:
            result=integrate(env,belief,3,seed,'rollout',selector_for(samples))
            assert result['errors']>=c['optimal']-1e-9
            rows.append(dict(graph=c['seed'],profile=c['profile'],seed=seed,samples=samples,
                             greedy_errors=reference['results']['greedy']['errors'],
                             reference_1024_errors=reference['results']['rollout']['errors'],**result))
        if seed==3:
            (args.out/'cases.json').write_text(json.dumps(rows,indent=2)+'\n')
            print(c['seed'],c['profile'],'complete',flush=True)
    summary=[]
    for profile in ['normal-confidence','type-prior']:
        for samples in manifest['samples']:
            cell=[r for r in rows if r['profile']==profile and r['samples']==samples]
            gains=[r['greedy_errors']-r['errors'] for r in cell]
            reference_gain=float(np.mean([r['greedy_errors']-r['reference_1024_errors'] for r in cell]))
            gain=float(np.mean(gains))
            summary.append(dict(profile=profile,samples=samples,cases=len(cell),
                                **{k:float(np.mean([r[k] for r in cell])) for k in ['errors','expected_simulated_reviews','tree_seconds']},
                                gain=gain,reference_1024_gain=reference_gain,
                                retained_gain_fraction=gain/reference_gain if reference_gain else None,
                                wins=sum(g>1e-9 for g in gains),losses=sum(g < -1e-9 for g in gains),
                                ties=sum(abs(g)<=1e-9 for g in gains)))
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    manifest.update(status='completed',trees=len(rows),output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.iterdir() if p.name!='manifest.json'})
    save();print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    main()
