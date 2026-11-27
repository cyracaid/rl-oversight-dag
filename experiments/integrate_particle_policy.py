#!/usr/bin/env python3
"""Integrate true feedback branches while retaining actual particle-policy state."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from belief import ParticleBelief
from exact_small_graph import ExactReview
from sampled_planning import choose
from run_full_episode_guard import continuation
from validate_selection_guard import accept


def decision(belief, available, remaining, step, seed, method):
    greedy=belief.best_action(available);action=greedy
    search=None;validation=None;reviews=0
    if method!='greedy':
        action,search=choose(belief,available,remaining,1024,belief.N,
                             seed*100000+1024+step*1000000)
        reviews+=search['simulated_reviews']
    proposed=action
    if method=='guarded' and action!=greedy:
        validation_seed=7000000+seed*100000+step*1000000
        d=(continuation(belief,available,remaining,action,validation_seed)
           -continuation(belief,available,remaining,greedy,validation_seed))
        passed=accept(d)
        validation=dict(passed=passed,mean=float(d.mean()),
                        standard_error=float(d.std(ddof=1)/np.sqrt(len(d))),
                        discordant=int(np.count_nonzero(d)))
        reviews+=2*1024*remaining
        if not passed:
            action=greedy
    return action,dict(greedy=greedy,proposed=proposed,search=search,
                       validation=validation,simulated_reviews=reviews)


def integrate(env, belief, budget, seed, method, selector=decision):
    tree=[];leaf_mass=0.;expected_reviews=0.;expected_degeneracies=0.
    tick=time.perf_counter()
    def visit(weights, cleared, posterior, available, step, history):
        nonlocal leaf_mass,expected_reviews,expected_degeneracies
        mass=float(weights.sum())
        if step==budget:
            cost=float(weights@env.state(cleared)[1])
            leaf_mass+=mass
            expected_degeneracies+=mass*posterior.n_degenerate
            tree.append(dict(history=history,mass=mass,weighted_errors=cost))
            return cost
        # Exact weights are deliberately not an argument of the selector.
        action,detail=selector(posterior,available,budget-step,step,seed,method)
        if not available[action]:
            raise AssertionError('reviewed action selected')
        expected_reviews+=mass*detail['simulated_reviews']
        tree.append(dict(history=history,mass=mass,action=action,detail=detail))
        value=0.
        for flagged,(branch,nc) in enumerate(env.branches(weights,cleared,action)):
            if branch.sum()==0:
                continue
            child=copy.deepcopy(posterior)
            child.observe(action,bool(flagged))
            mask=list(available);mask[action]=False
            value+=visit(branch,nc,child,mask,step+1,history+[[action,flagged]])
        return value
    value=visit(env.weights,0,copy.deepcopy(belief),[True]*belief.N,0,[])
    if abs(leaf_mass-1.)>1e-10:
        raise AssertionError('leaf probability mass not conserved')
    return dict(errors=value,leaf_mass=leaf_mass,expected_simulated_reviews=expected_reviews,
                expected_degeneracies=expected_degeneracies,tree_seconds=time.perf_counter()-tick,tree=tree)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    source=Path('runs/small-graph-conditioned-v1/cases.json')
    receipt=json.loads(source.with_name('manifest.json').read_text())
    assert hashlib.sha256(source.read_bytes()).hexdigest()==receipt['output_sha256']['cases.json']
    cases=[c for c in json.loads(source.read_text()) if c['budget']==3]
    args.out.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).parent
    names=['integrate_particle_policy.py','exact_small_graph.py','belief.py','sampled_planning.py',
           'run_full_episode_guard.py','validate_selection_guard.py','EXACT_POLICY_PROTOCOL.md']
    manifest=dict(status='in_progress',seeds=list(range(4)),particles=1024,samples=1024,budget=3,
                  input_sha256={str(source):hashlib.sha256(source.read_bytes()).hexdigest()},
                  source_sha256={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names})
    def save():
        (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    save();rows=[]
    for c in cases:
        prior=c['conditioned_prior'] if c['profile']=='normal-confidence' else c['type_prior']
        env=ExactReview(c['parents'],prior,sinks=c['sinks'])
        edges={(p,i):.6 for i,ps in enumerate(c['parents']) for p in ps}
        for seed in manifest['seeds']:
            b=ParticleBelief(c['parents'],range(6),c['sinks'],edges,prior,.9,1024,seed+50000)
            results={method:integrate(env,b,3,seed,method) for method in ['greedy','rollout','guarded']}
            for r in results.values():
                assert r['errors']>=c['optimal']-1e-9
            rows.append(dict(graph=c['seed'],profile=c['profile'],seed=seed,
                             exact_optimal=c['optimal'],exact_greedy=c['greedy'],results=results))
        (args.out/'cases.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(c['seed'],c['profile'],'complete',flush=True)
    summary=[]
    for profile in ['normal-confidence','type-prior']:
        cell=[r for r in rows if r['profile']==profile]
        for method in ['greedy','rollout','guarded']:
            delta=[r['results'][method]['errors']-r['results']['greedy']['errors'] for r in cell]
            summary.append(dict(profile=profile,method=method,cases=len(cell),
                                **{k:float(np.mean([r['results'][method][k] for r in cell])) for k in
                                   ['errors','expected_simulated_reviews','expected_degeneracies','tree_seconds']},
                                delta=float(np.mean(delta)),wins=sum(d < -1e-9 for d in delta),
                                losses=sum(d > 1e-9 for d in delta),ties=sum(abs(d)<=1e-9 for d in delta)))
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    manifest.update(status='completed',triples=len(rows),output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.iterdir() if p.name!='manifest.json'})
    save();print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    main()
